from decimal import Decimal

import pytest
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
