from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from payments import PaymentStatus, RedirectNeeded, get_payment_model
from payments.core import BasicProvider
from payments.models import BasePayment

from .facade import Facade

Payment = get_payment_model()


class MollieProvider(
    BasicProvider  # type: ignore[misc] # django-payments types are unavailable
):
    """
    Django Payments provider class for Mollie.
    """

    facade: Facade

    def __init__(self, api_key: str = "") -> None:
        """
        Init a new provider instance.

        The arguments for this method are the values in the configuration dict
        in the PAYMENT_VARIANTS definition.
        """
        self.facade = Facade()
        self.facade.setup_with_api_key(api_key)

    @staticmethod
    def update_payment(payment_id: int, **kwargs: Any) -> None:
        """
        Helper method to update the payment model safely.

        See https://django-payments.readthedocs.io/en/latest/payment-model.html#mutating-a-payment-instance  # noqa: E501
        """
        Payment.objects.filter(id=payment_id).update(**kwargs)

    def get_form(self, payment: BasePayment, data: Any = None) -> None:
        """
        Return a form that collects payment-specific data, or redirect to the PSP.

        The form can request billing details, a specific payment method or even CC
        details from the user. Entered Form values are returned in the `data` argument.
        The Payment instance may be updated with the retrieved data. Then the
        payment at Mollie can be created, and the user should be redirected
        to the Mollie checkout.

        For now, we don't need any details, so we'll just create the Mollie payment
        and send the user to the checkout.
        """
        return_url = self.get_return_url(payment)
        mollie_payment = self.facade.create_payment(payment, return_url)

        # Update the Payment
        self.update_payment(payment.id, transaction_id=mollie_payment.id)
        payment.change_status(PaymentStatus.INPUT)

        # Send the user to Mollie for further payment
        raise RedirectNeeded(mollie_payment.checkout_url)

    def process_data(self, payment: BasePayment, request: HttpRequest) -> HttpResponse:
        """
        Handle payment changes from Mollie.

        This method is called by the endpoint that is sent to Mollie as
        `redirectUrl` and/or `webhookUrl`. There are two types of requests:

        1) The user has completed a payment workflow at Mollie, and returns back to
        the application. This is typically a GET request. For this case, we need to
        update the local payment, and finally redirect the user to the success or
        failure URL.

        2) Mollie has some updates on the payment, and calls the webhook to notify us of
        these. This is typically a POST request. If this happens, we also need to update
        the local payment, and then tell Mollie that we processed the webhook request
        (i.e. return a HTTP 200).

        See https://docs.mollie.com/overview/webhooks for details.
        """
        allowed_methods = ["GET", "POST"]
        if request.method not in allowed_methods:
            return HttpResponseNotAllowed(allowed_methods)

        mollie_payment = self.facade.retrieve_payment(payment)
        (
            next_status,
            next_status_message,
            payment_updates,
        ) = self.facade.parse_payment_status(mollie_payment)

        # Update the payment
        # TODO: Don't update if the status hasn't changed?
        if next_status:
            payment.change_status(next_status, next_status_message)
            if (
                next_status == PaymentStatus.CONFIRMED
                and "captured_amount" not in payment_updates
            ):
                payment_updates["captured_amount"] = payment.total

        if payment_updates:
            self.update_payment(payment.id, **payment_updates)

        if request.method == "POST":
            # Return a HTTP 200 to the Mollie webhook
            return HttpResponse(b"webhook processed")
        else:
            # The request was a user getting redirected after a payment
            if next_status in (PaymentStatus.CONFIRMED, PaymentStatus.PREAUTH):
                return redirect(payment.get_success_url())
            else:
                return redirect(payment.get_failure_url())
