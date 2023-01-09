import json
from typing import Any, Optional

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from mollie.api.client import Client as MollieClient
from mollie.api.error import Error as MollieError
from mollie.api.objects.payment import Payment as MolliePayment
from payments import PaymentError, PaymentStatus, RedirectNeeded, get_payment_model
from payments.core import BasicProvider
from payments.models import BasePayment

Payment = get_payment_model()


class MolliePaymentStatus:
    """
    Mollie payment statuses
    See https://docs.mollie.com/payments/status-changes#every-possible-payment-status
    """

    OPEN: str = "open"
    CANCELED: str = "canceled"
    PENDING: str = "pending"
    AUTHORIZED: str = "authorized"
    EXPIRED: str = "expired"
    FAILED: str = "failed"
    PAID: str = "paid"


class MollieProvider(
    BasicProvider  # type: ignore[misc] # django-payments types are unavailable
):
    """
    Django-payments provider class for Mollie.
    """

    client: MollieClient

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        testmode: bool = False,
    ) -> None:
        self.client = MollieClient()

        if api_key:
            self.client.set_api_key(api_key)
        elif access_token:
            self.client.set_access_token(access_token)

        if testmode:
            self.client.set_testmode(testmode)

    def get_form(self, payment: BasePayment, data: Any = None) -> None:
        """
        Render the form that we show when creating a new payment.

        We don't need a form now, so we create the payment at Mollie,
        and redirect the user to the remote checkout URL.

        In the future, we could implement the form to request
        the Mollie payment method, CC details, etc
        """
        mollie_payment = self.create_remote_payment(payment)

        # Update our local payment
        Payment.objects.filter(id=payment.id).update(transaction_id=mollie_payment.id)

        # Update payment status
        payment.change_status(PaymentStatus.INPUT)

        # Send the user to Mollie for further payment
        raise RedirectNeeded(mollie_payment.checkout_url)

    def process_data(self, payment: BasePayment, request: HttpRequest) -> HttpResponse:
        """
        Process callback request from a payment provider.

        This method should handle checking the status of the payment, and
        update the ``payment`` instance.
        If a client is redirected here after making a payment, then this view
        should redirect them to either :meth:`Payment.get_success_url` or
        :meth:`Payment.get_failure_url`.

        Note: This method receives both customer browser requests (redirects from
        the PSP) as webhook requests by the PSP without direct user interaction.
        Webhook requests are not yet implemented.
        """
        mollie_payment = self.retrieve_remote_payment(payment)

        next_status = None
        next_status_message = ""
        payment_updates = {"extra_data": json.dumps(mollie_payment)}

        if mollie_payment.status == MolliePaymentStatus.PAID:
            next_status = PaymentStatus.CONFIRMED
            payment_updates["captured_amount"] = payment.total

        elif mollie_payment.status in [
            MolliePaymentStatus.CANCELED,
            MolliePaymentStatus.EXPIRED,
            MolliePaymentStatus.FAILED,
        ]:
            next_status = PaymentStatus.REJECTED
            next_status_message = f"Mollie returned status '{mollie_payment.status}'"

        elif mollie_payment.status in [
            MolliePaymentStatus.OPEN,
            MolliePaymentStatus.PENDING,
        ]:
            # Customer has not completed the flow at Mollie yet, or has completed
            # the flow but Mollie has not started processing
            pass

        else:
            # Note: AUTHORIZED is not listed above, as
            # it never happens with Payments (only Orders).
            next_status = PaymentStatus.ERROR
            next_status_message = (
                f"Mollie returned unexpected status '{mollie_payment.status}'"
            )

        # Update the payment
        if next_status:
            payment.change_status(next_status, next_status_message)
        if payment_updates:
            Payment.objects.filter(id=payment.id).update(**payment_updates)

        # Send the customer off
        if next_status in (PaymentStatus.CONFIRMED, PaymentStatus.PREAUTH):
            return redirect(payment.get_success_url())
        else:
            return redirect(payment.get_failure_url())

    def create_remote_payment(self, payment: BasePayment) -> MolliePayment:
        """Create a payment at Mollie, or raise a PaymentError"""
        if payment.status != PaymentStatus.WAITING:
            raise PaymentError(_("Payment status is incorrect"))

        if not payment.currency:
            # This is a programming error
            raise ValueError("The payment has no currency, but it is required")
        if not payment.total:
            # This is a programming error
            raise ValueError("The payment has no total amount, but it is required")

        payload = {
            "amount": {
                "currency": payment.currency,
                "value": str(payment.total),
            },
            "description": payment.description,
            "redirectUrl": self.get_return_url(payment),
        }

        try:
            mollie_payment = self.client.payments.create(payload)
        except MollieError as exc:
            raise PaymentError(
                _("Failed to create payment"),
                gateway_message=str(exc),
            )

        return mollie_payment  # type: ignore[no-any-return]  # upstream types as Any

    def retrieve_remote_payment(self, payment: BasePayment) -> MolliePayment:
        if not payment.transaction_id:
            raise PaymentError(_("Mollie payment id is unknown"))

        mollie_payment = self.client.payments.get(payment.transaction_id)
        return mollie_payment
