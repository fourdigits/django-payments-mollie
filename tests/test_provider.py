from decimal import Decimal
from http import HTTPStatus

import pytest
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from payments import PaymentStatus, RedirectNeeded
from payments.core import provider_factory

from django_payments_mollie.facade import Facade
from django_payments_mollie.provider import MollieProvider

from .factories import PaymentFactory

pytestmark = pytest.mark.django_db


def test_get_provider_from_settings(mocker):
    # Ensure we don't get coverage for the facade from this test
    mocker.patch("django_payments_mollie.provider.Facade.setup_with_api_key")

    provider = provider_factory("mollie")
    assert isinstance(provider, MollieProvider)
    assert provider.facade, "Facade should be initialized"
    assert isinstance(provider.facade, Facade)


def test_provider_initializes_facade(mocker):
    mocker.patch("django_payments_mollie.provider.Facade.setup_with_api_key")
    provider = MollieProvider(api_key="test_test")

    provider.facade.setup_with_api_key.assert_called_once_with("test_test")


def test_provider_get_form_creates_mollie_payment(mocker, mollie_payment):
    mocker.patch("django_payments_mollie.provider.Facade")

    provider = MollieProvider(api_key="test_test")
    # Configure mock
    provider.facade.create_payment.return_value = mollie_payment

    payment = PaymentFactory()
    with pytest.raises(RedirectNeeded):
        provider.get_form(payment)

    provider.facade.create_payment.assert_called_once()

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.INPUT
    assert (
        payment.transaction_id == mollie_payment.id
    ), "Mollie payment ID should be saved"


def test_provider_get_form_redirects_to_mollie(mocker, mollie_payment):
    mocker.patch("django_payments_mollie.provider.Facade")

    provider = MollieProvider(api_key="test_test")
    # Configure mock
    provider.facade.create_payment.return_value = mollie_payment

    payment = PaymentFactory()
    with pytest.raises(RedirectNeeded) as excinfo:
        provider.get_form(payment)

    assert excinfo.type == RedirectNeeded
    assert str(excinfo.value) == mollie_payment.checkout_url


def test_provider_process_data_updates_payment(mocker):
    mocker.patch("django_payments_mollie.provider.Facade")

    provider = MollieProvider(api_key="test_test")
    # Configure mock
    provider.facade.parse_payment_status.return_value = (
        PaymentStatus.CONFIRMED,
        "payment confirmed",
        {"captured_amount": "13.37"},
    )

    payment = PaymentFactory()
    request = HttpRequest()
    request.method = "GET"

    provider.process_data(payment, request)

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.message == "payment confirmed"
    assert payment.captured_amount == Decimal("13.37")


def test_provider_process_data_confirmed_payment_uses_own_amount(mocker):
    """If Mollie returns no captured amount, the `payment.total` is used."""
    mocker.patch("django_payments_mollie.provider.Facade")

    provider = MollieProvider(api_key="test_test")
    # Configure mock
    provider.facade.parse_payment_status.return_value = (
        PaymentStatus.CONFIRMED,
        "",
        {},
    )

    payment = PaymentFactory(total="47")
    request = HttpRequest()
    request.method = "GET"

    provider.process_data(payment, request)

    payment.refresh_from_db()
    assert payment.captured_amount == Decimal("47.00")


@pytest.mark.parametrize(
    "status, redirect",
    [
        (PaymentStatus.CONFIRMED, "success"),
        (PaymentStatus.PREAUTH, "success"),
        (PaymentStatus.REJECTED, "failure"),
        (PaymentStatus.ERROR, "failure"),
    ],
)
def test_provider_process_data_returns_result_redirect(mocker, status, redirect):
    mocker.patch("django_payments_mollie.provider.Facade")

    provider = MollieProvider(api_key="test_test")
    # Configure mock
    provider.facade.parse_payment_status.return_value = (
        status,  # Set from parametrized value
        "",
        {},
    )

    payment = PaymentFactory(total="47")
    request = HttpRequest()
    request.method = "GET"

    result = provider.process_data(payment, request)
    assert isinstance(result, HttpResponseRedirect)
    assert result.url == f"https://example.com/{redirect}"


def test_provider_process_data_webhook_request_returns_http_200(mocker):
    mocker.patch("django_payments_mollie.provider.Facade")

    provider = MollieProvider(api_key="test_test")
    # Configure mock
    provider.facade.parse_payment_status.return_value = (
        PaymentStatus.CONFIRMED,
        "",
        {},
    )

    payment = PaymentFactory()
    webhook_request = HttpRequest()
    webhook_request.method = "POST"

    result = provider.process_data(payment, webhook_request)
    assert isinstance(result, HttpResponse)
    assert result.status_code == HTTPStatus.OK
