import json
import warnings
from decimal import Decimal
from typing import Any, Dict, Tuple

from django.utils.translation import gettext_lazy as _
from mollie.api.client import Client as MollieClient
from mollie.api.error import Error as MollieError
from mollie.api.objects.payment import Payment as MolliePayment
from payments import FraudStatus, PaymentError, PaymentStatus
from payments.models import BasePayment

from . import __version__ as version


class Facade:
    """
    Interface between Django payments and Mollie.

    In this class, all functionality that actually touches Mollie is implemented.
    """

    client: MollieClient

    def __init__(self) -> None:
        self.client = MollieClient()
        self.client.set_user_agent_component("Django Payments Mollie", version)

    def setup_with_api_key(self, api_key: str) -> None:
        """Setup the Mollie client using an API key."""
        self.client.set_api_key(api_key)

    def retrieve_payment(self, payment: BasePayment) -> MolliePayment:
        """Retrieve a payment at Mollie."""
        if not payment.transaction_id:
            raise PaymentError(_("Mollie payment id is unknown"))

        try:
            mollie_payment = self.client.payments.get(payment.transaction_id)
        except MollieError as exc:
            raise PaymentError(
                _("Failed to retrieve payment at Mollie"),
                gateway_message=exc,
            )

        return mollie_payment

    def create_payment(self, payment: BasePayment, return_url: str) -> MolliePayment:
        """Create a new payment at Mollie."""
        if payment.status != PaymentStatus.WAITING:
            raise PaymentError(_("Payment status is not WAITING"))

        if not payment.currency:
            # This is a programming error
            raise ValueError("The payment has no currency, but it is required")
        if not payment.total:
            # This is a programming error
            raise ValueError("The payment has no total amount, but it is required")

        payload = self._generate_new_payment_payload(payment, return_url)
        try:
            mollie_payment = self.client.payments.create(payload)
        except MollieError as exc:
            payment.change_status(PaymentStatus.ERROR, str(exc))
            raise PaymentError(
                _("Failed to create payment at Mollie"),
                gateway_message=exc,
            )

        return mollie_payment  # type: ignore[no-any-return]  # .get() has generic type

    @staticmethod
    def parse_payment_status(
        mollie_payment: MolliePayment,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Parse a Mollie payment response and extract all relevant status data.

        Returns a tuple containing:
        - The Payment status (from `payments.PaymentStatus`)
        - The Payment status message
        - A dictionary of other Payment fields that need updating
        """
        next_status = ""
        next_status_message = ""
        # Save the full payment response to the extra_data field for later reference
        payment_updates = {"extra_data": json.dumps(mollie_payment)}

        if mollie_payment.is_paid():  # type: ignore[no-untyped-call]
            next_status = PaymentStatus.CONFIRMED
            if mollie_payment.amount_captured:
                payment_updates[
                    "captured_amount"
                ] = Decimal(  # type:ignore[assignment]  # django-payments has a str default on the decimal field  # noqa: E501
                    mollie_payment.amount_captured["value"]
                )

        elif mollie_payment.is_canceled() or mollie_payment.is_expired():  # type: ignore[no-untyped-call]  # noqa: E501
            next_status = PaymentStatus.REJECTED
            next_status_message = (
                f"Mollie payment failed with status '{mollie_payment.status}'"
            )
        elif mollie_payment.is_failed():  # type: ignore[no-untyped-call]
            next_status = PaymentStatus.REJECTED
            next_status_message = (
                f"Mollie payment failed with status '{mollie_payment.status}'"
            )

            if mollie_payment.details:
                failure_reason = mollie_payment.details.get("failureReason", "")
                if failure_reason:
                    next_status_message += f" reason='{failure_reason}'"

                failure_message = mollie_payment.details.get("failureMessage", "")
                if failure_message:
                    next_status_message += f" message='{failure_message}'"

                if failure_reason == "possible_fraud":
                    payment_updates["fraud_status"] = FraudStatus.REJECT
                    payment_updates["fraud_message"] = failure_message

        elif mollie_payment.is_open() or mollie_payment.is_pending():  # type: ignore[no-untyped-call]  # noqa: E501
            # Payment flow isn't completed by the User or Mollie (yet)
            pass

        else:
            # Note: status=AUTHORIZED is not handled above, as
            # it never happens with Payments (only Orders).
            next_status = PaymentStatus.ERROR
            next_status_message = (
                f"Mollie returned unexpected status '{mollie_payment.status}'"
            )

        return next_status, next_status_message, payment_updates

    @classmethod
    def _generate_new_payment_payload(
        cls,
        payment: BasePayment,
        return_url: str,
    ) -> Dict[str, Any]:
        """Generate the payload for a new Mollie payment request."""
        payload = {
            "amount": {
                "currency": payment.currency,
                "value": str(payment.total),
            },
            "description": payment.description,
            "redirectUrl": return_url,
        }

        # Add billing address if possible
        billing_address = cls._generate_billing_address(payment)
        if billing_address:
            payload["billingAddress"] = billing_address

        return payload

    @classmethod
    def _generate_billing_address(cls, payment: BasePayment) -> Dict[str, str]:
        """
        Generate a billing adress dict from the payment data.

        Note: some address details are required by the Mollie API when providing a
        billing address. If you don't provide data in the payment model fields
        `billing_address_1`, `billing_city` and `billing_country`, no billing address
        will be generated.

        See https://docs.mollie.com/overview/common-data-types#address-object
        """
        billing_address = {}

        # Check if all required address details are available
        if not (
            payment.billing_address_1
            and payment.billing_city
            and payment.billing_country_code
        ):
            # Check if some required address details are set
            if (
                payment.billing_address_1
                or payment.billing_city
                or payment.billing_country_code
            ):
                warnings.warn(
                    "Some billing address details are set in the payment object, but "
                    "not enough to fulfill Mollie requirements, omitting the billing "
                    "address.",
                    UserWarning,
                )

            return {}

        if payment.billing_address_1:
            billing_address["streetAndNumber"] = payment.billing_address_1

        if payment.billing_address_2 and billing_address["streetAndNumber"]:
            billing_address["streetAndNumber"] += f" {payment.billing_address_2}"

        if payment.billing_postcode:
            billing_address["postalCode"] = payment.billing_postcode

        if payment.billing_city:
            billing_address["city"] = payment.billing_city

        if payment.billing_country_area:
            billing_address["region"] = payment.billing_country_area

        if payment.billing_country_code:
            billing_address["country"] = payment.billing_country_code

        return billing_address
