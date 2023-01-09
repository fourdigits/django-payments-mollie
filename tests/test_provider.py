from decimal import Decimal

import pytest
from payments import PaymentStatus
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
