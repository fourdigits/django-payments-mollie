import json
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse
from payments import get_payment_model

pytestmark = pytest.mark.django_db


def test_create_payment():
    Payment = get_payment_model()
    payment = Payment.objects.create(
        variant="mollie",
        description="Book purchase",
        total=Decimal(120),
        tax=Decimal(20),
        currency="USD",
        delivery=Decimal(10),
        billing_first_name="Sherlock",
        billing_last_name="Holmes",
        billing_address_1="221B Baker Street",
        billing_address_2="",
        billing_city="London",
        billing_postcode="NW1 6XE",
        billing_country_code="GB",
        billing_country_area="Greater London",
        customer_ip_address="127.0.0.1",
    )

    assert payment.status == "waiting"
    assert payment.total == Decimal(120)
    assert payment.captured_amount == "0.0"


def test_create_payment_submits_data_to_mollie(django_app, responses):
    responses.post("https://api.mollie.com/v2/payments", json="payment")

    Payment = get_payment_model()
    payment = Payment.objects.create(
        variant="mollie",
        description="Book purchase",
        total=Decimal(120),
        currency="EUR",
    )

    url = reverse("payment-details", kwargs={"payment_id": payment.id})
    resp = django_app.get(url)
    assert resp.status_code == HTTPStatus.FOUND
    assert resp.location == "https://www.mollie.com/payscreen/select-method/7UhSN1zuXS"

    assert len(responses.calls) == 1
    payload = json.loads(responses.calls[-1].request.body)
    assert payload["amount"] == {"value": "120.00", "currency": "EUR"}
    assert payload["description"] == "Book purchase"

    payment.refresh_from_db()
    assert (
        payment.transaction_id == "tr_7UhSN1zuXS"
    ), "Payment id from Mollie should be saved"
