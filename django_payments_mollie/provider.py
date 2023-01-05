from typing import Any, Optional

from django.utils.translation import gettext_lazy as _
from mollie.api.client import Client as MollieClient
from mollie.api.error import Error as MollieError
from mollie.api.objects.payment import Payment as MolliePayment
from payments import PaymentError, PaymentStatus, RedirectNeeded, get_payment_model
from payments.core import BasicProvider
from payments.models import BasePayment

Payment = get_payment_model()


class MollieProvider(
    BasicProvider  # type: ignore[misc] # django-payments types are unavailable
):
    """
    Django-payments provider class for Mollie.
    """

    client: MollieClient
    capture: bool

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        testmode: bool = False,
        capture: bool = False,
    ) -> None:
        self.client = MollieClient()
        self.capture = capture

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
