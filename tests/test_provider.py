from decimal import Decimal

import pytest
from payments import PaymentError, PaymentStatus
from payments.core import provider_factory

from .factories import PaymentFactory

pytestmark = pytest.mark.django_db


def test_get_provider_from_settings():
    provider = provider_factory("mollie")

    assert provider.client is not None, "Internal mollie client is unavailable"
    assert provider.client.testmode is True, "Testmode is not adopted correctly"


def test_process_data_updates_payment_after_success(responses):
    responses.get(
        "https://api.mollie.com/v2/payments/tr_12345", mock_json="payment_paid"
    )

    provider = provider_factory("mollie")
    payment = PaymentFactory(submitted=True)
    result = provider.process_data(payment, None)
    assert "/success/" in result.url

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.captured_amount == payment.total
    assert '"status": "paid"' in payment.extra_data


def test_process_data_updates_payment_after_failure(responses):
    responses.get(
        "https://api.mollie.com/v2/payments/tr_12345", mock_json="payment_failed"
    )

    provider = provider_factory("mollie")
    payment = PaymentFactory(submitted=True)
    result = provider.process_data(payment, None)
    assert "/failure/" in result.url

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.REJECTED
    assert payment.message == "Mollie returned status 'failed'"
    assert payment.captured_amount == Decimal(0)
    assert '"status": "failed"' in payment.extra_data


def test_process_data_updates_payment_after_unknown_status(responses):
    responses.get(
        "https://api.mollie.com/v2/payments/tr_12345",
        mock_json="payment_unknown_status",
    )

    provider = provider_factory("mollie")
    payment = PaymentFactory(submitted=True)
    result = provider.process_data(payment, None)
    assert "/failure/" in result.url

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.ERROR
    assert payment.message == "Mollie returned unexpected status 'hoeba'"
    assert payment.captured_amount == Decimal(0)
    assert '"status": "hoeba"' in payment.extra_data


def test_provider_updates_payment_upon_create_api_failure(responses):

    provider = provider_factory("mollie")
    payment = PaymentFactory()

    with pytest.raises(PaymentError):
        provider.create_remote_payment(payment)

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.ERROR
    assert (
        "Unable to communicate with Mollie: Connection refused by Responses"
        in payment.message
    )


def test_provider_updates_payment_upon_retrieve_api_failure(responses):

    provider = provider_factory("mollie")
    payment = PaymentFactory(submitted=True)

    with pytest.raises(PaymentError):
        provider.retrieve_remote_payment(payment)

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.ERROR
    assert (
        "Unable to communicate with Mollie: Connection refused by Responses"
        in payment.message
    )
