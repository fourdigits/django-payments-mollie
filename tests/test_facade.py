from decimal import Decimal

import pytest
from mollie.api.client import Client as MollieClient
from mollie.api.error import ResponseHandlingError
from mollie.api.objects.payment import Payment as MolliePayment
from payments import FraudStatus, PaymentError, PaymentStatus

from django_payments_mollie import __version__ as version
from django_payments_mollie.facade import Facade

from .factories import PaymentFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="function")
def facade(mocker):
    """A Facade instance configured with an API key, and patched Mollie resources"""
    mocker.patch("mollie.api.client.Payments")

    facade = Facade()
    facade.setup_with_api_key("test_test")
    return facade


def test_facade_configures_mollie_user_agent():
    facade = Facade()

    assert facade.client, "Client should have been initialized"
    assert isinstance(facade.client, MollieClient)

    assert f"DjangoPaymentsMollie/{version}" in facade.client.user_agent


def test_facade_configures_api_key(mocker):

    facade = Facade()
    spy = mocker.spy(facade.client, "set_api_key")

    facade.setup_with_api_key("test_test")

    spy.assert_called_once_with("test_test")


def test_facade_retrieve_payment(facade, mollie_payment):
    facade.client.payments.get.return_value = mollie_payment

    payment = PaymentFactory(submitted=True)
    resp = facade.retrieve_payment(payment)

    assert isinstance(resp, MolliePayment)


def test_facade_retrieve_payment_mollie_error(facade):
    facade.client.payments.get.side_effect = ResponseHandlingError(
        "Unable to decode Mollie API response (status code: 404): ''."
    )

    payment = PaymentFactory(submitted=True)
    with pytest.raises(PaymentError) as excinfo:
        facade.retrieve_payment(payment)

    assert str(excinfo.value) == "Failed to retrieve payment at Mollie"
    assert (
        str(excinfo.value.gateway_message)
        == "Unable to decode Mollie API response (status code: 404): ''."
    )


def test_facade_create_payment(facade, mollie_payment):
    facade.client.payments.create.return_value = mollie_payment

    payment = PaymentFactory()
    resp = facade.create_payment(payment, "https://example.com/return-url/")
    assert isinstance(resp, MolliePayment)

    expected_payload = {
        "amount": {
            "currency": payment.currency,
            "value": str(payment.total),
        },
        "description": payment.description,
        "redirectUrl": "https://example.com/return-url/",
    }
    facade.client.payments.create.assert_called_once_with(expected_payload)


def test_facade_create_payment_payment_status_error(facade):
    payment = PaymentFactory(status=PaymentStatus.CONFIRMED)

    with pytest.raises(PaymentError) as excinfo:
        facade.create_payment(payment, "https://example.com/return-url/")
    assert str(excinfo.value) == "Payment status is not WAITING"


def test_facade_create_payment_mollie_error(facade):
    facade.client.payments.create.side_effect = ResponseHandlingError(
        "Unable to decode Mollie API response (status code: 400): ''."
    )

    payment = PaymentFactory()
    with pytest.raises(PaymentError) as excinfo:
        facade.create_payment(payment, "https://example.com/return-url/")
    assert str(excinfo.value) == "Failed to create payment at Mollie"
    assert (
        str(excinfo.value.gateway_message)
        == "Unable to decode Mollie API response (status code: 400): ''."
    )


def test_facade_create_payment_sanity_checks(facade):
    payment_no_currency = PaymentFactory(currency="")

    with pytest.raises(ValueError) as excinfo:
        facade.create_payment(payment_no_currency, "https://example.com/return-url/")
    assert str(excinfo.value) == "The payment has no currency, but it is required"

    payment_no_total = PaymentFactory(total=Decimal("0"))

    with pytest.raises(ValueError) as excinfo:
        facade.create_payment(payment_no_total, "https://example.com/return-url/")
    assert str(excinfo.value) == "The payment has no total amount, but it is required"


def test_facade_create_payment_adds_full_billing_address(facade):
    payment = PaymentFactory(
        billing_address_1="Street 1",
        billing_address_2="Building 47",
        billing_postcode="1234AB",
        billing_city="That Never Sleeps",
        billing_country_area="Hoeba Area",
        billing_country_code="NL",
    )
    facade.create_payment(payment, "https://example.com/return-url/")

    expected_payload = {
        "billingAddress": {
            "streetAndNumber": "Street 1 Building 47",
            "postalCode": "1234AB",
            "city": "That Never Sleeps",
            "region": "Hoeba Area",
            "country": "NL",
        },
        "amount": {
            "currency": payment.currency,
            "value": str(payment.total),
        },
        "description": payment.description,
        "redirectUrl": "https://example.com/return-url/",
    }
    facade.client.payments.create.assert_called_once_with(
        expected_payload
    ), "Payload should contain billingAddress"


@pytest.mark.parametrize(
    "omit_kwarg",
    [
        "billing_address_1",
        "billing_city",
        "billing_country_code",
    ],
)
def test_facade_create_payment_incomplete_billing_address_warning(facade, omit_kwarg):
    factory_kwargs = {
        "billing_address_1": "Street 1",
        "billing_city": "That Never Sleeps",
        "billing_country_code": "NL",
    }
    del factory_kwargs[omit_kwarg]
    payment = PaymentFactory(**factory_kwargs)
    assert getattr(payment, omit_kwarg) == ""  # sanity check

    with pytest.warns(UserWarning) as warninfo:
        facade.create_payment(payment, "https://example.com/return-url/")

    assert (
        str(warninfo[0].message)
        == "Some billing address details are set in the payment object, but not enough to fulfill Mollie requirements, omitting the billing address."  # noqa: E501
    )

    expected_payload = {
        "amount": {
            "currency": payment.currency,
            "value": str(payment.total),
        },
        "description": payment.description,
        "redirectUrl": "https://example.com/return-url/",
    }
    facade.client.payments.create.assert_called_once_with(
        expected_payload
    ), "Payload should not contain an incomplete billingAdddress"


@pytest.mark.parametrize(
    "payment_data, expected_status, expected_message, expected_updates",
    [
        (
            {"paidAt": "2018-03-20T09:28:37+00:00"},
            PaymentStatus.CONFIRMED,
            "",
            {},
        ),
        (
            {
                "paidAt": "2018-03-20T09:28:37+00:00",
                "amountCaptured": {"value": "13.37", "currency": "EUR"},
            },
            PaymentStatus.CONFIRMED,
            "",
            {"captured_amount": Decimal("13.37")},
        ),
        (
            {"status": "canceled"},
            PaymentStatus.REJECTED,
            "Mollie payment failed with status 'canceled'",
            {},
        ),
        (
            {"status": "expired"},
            PaymentStatus.REJECTED,
            "Mollie payment failed with status 'expired'",
            {},
        ),
        (
            {"status": "failed"},
            PaymentStatus.REJECTED,
            "Mollie payment failed with status 'failed'",
            {},
        ),
        (
            {"status": "open"},
            "",
            "",
            {},
        ),
        (
            {"status": "pending"},
            "",
            "",
            {},
        ),
        (
            {"status": "authorized"},
            PaymentStatus.ERROR,
            "Mollie returned unexpected status 'authorized'",
            {},
        ),
    ],
)
def test_facade_parse_payment_status(
    facade,
    mollie_payment,
    payment_data,
    expected_status,
    expected_message,
    expected_updates,
):
    mollie_payment = MolliePayment(payment_data, client=None)

    status, status_message, payment_updates = facade.parse_payment_status(
        mollie_payment
    )
    assert (
        "extra_data" in payment_updates
    ), "Payment updates should always contain the 'extra_data' field"

    assert status == expected_status
    assert status_message == expected_message

    # We don't want to assert the contants of extra_data
    del payment_updates["extra_data"]
    assert payment_updates == expected_updates


def test_facade_parse_payment_status_failure_details(facade):
    data = {
        "status": "failed",
        "details": {
            "failureReason": "some-reason",
            "failureMessage": "Details about failure",
        },
    }
    mollie_payment = MolliePayment(data, client=None)

    status, status_message, payment_updates = facade.parse_payment_status(
        mollie_payment
    )

    assert status == PaymentStatus.REJECTED
    assert (
        status_message
        == "Mollie payment failed with status 'failed' reason='some-reason' message='Details about failure'"  # noqa: E501
    )

    del payment_updates["extra_data"]
    assert payment_updates == {}


def test_facade_parse_payment_status_fraud_details(facade):
    data = {
        "status": "failed",
        "details": {
            "failureReason": "possible_fraud",
            "failureMessage": "Details about fraud",
        },
    }
    mollie_payment = MolliePayment(data, client=None)

    status, _, payment_updates = facade.parse_payment_status(mollie_payment)

    assert status == PaymentStatus.REJECTED
    del payment_updates["extra_data"]
    assert payment_updates == {
        "fraud_message": "Details about fraud",
        "fraud_status": FraudStatus.REJECT,
    }
