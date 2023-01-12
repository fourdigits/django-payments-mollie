import json
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


def test_provider_generates_billing_address(faker):
    provider = provider_factory("mollie")
    payment = PaymentFactory()

    street_address = faker.street_address()
    building_number = faker.building_number()
    postcode = faker.postcode()
    city = faker.city()
    region = "Gelderland"
    country = faker.country()
    country_code = faker.country_code()

    payment.billing_address_1 = street_address
    payment.billing_address_2 = building_number
    payment.billing_postcode = postcode
    payment.billing_city = city
    payment.billing_country_area = region
    payment.billing_country = country
    payment.billing_country_code = country_code
    payment.save()

    billing_address = provider._create_mollie_billing_address(payment)

    assert billing_address == {
        "streetAndNumber": f"{street_address} {building_number}",
        "postalCode": postcode,
        "city": city,
        "region": region,
        "country": country_code,
    }


@pytest.mark.parametrize(
    "field_to_omit", ["billing_address_1", "billing_city", "billing_country_code"]
)
def test_provider_omits_empty_or_partial_billing_address(
    responses, faker, field_to_omit
):
    responses.post("https://api.mollie.com/v2/payments", mock_json="payment_new")

    provider = provider_factory("mollie")
    payment = PaymentFactory()

    payment.billing_address_1 = faker.street_address()
    payment.billing_address_2 = faker.building_number()
    payment.billing_postcode = faker.postcode()
    payment.billing_city = faker.city()
    payment.billing_country_area = "Gelderland"
    payment.billing_country = faker.country()
    payment.billing_country_code = faker.country_code()

    setattr(payment, field_to_omit, "")
    payment.save()

    billing_address = provider._create_mollie_billing_address(payment)
    assert billing_address == {}, "An empty billing address should be returned"

    provider.create_remote_payment(payment)

    assert len(responses.calls) == 1
    request = responses.calls[-1].request
    payload = json.loads(request.body)
    assert (
        "billingAddress" not in payload
    ), "Billing address should not be sent to Mollie"
