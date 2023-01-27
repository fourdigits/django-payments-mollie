import pytest
from faker import Faker

fake = Faker()


@pytest.fixture
def mollie_payment():
    from mollie.api.objects.payment import Payment

    transaction_id = f"tr_{fake.password(length=10, special_chars=False)}"
    currency = fake.currency_code()
    amount = fake.pydecimal(right_digits=2, min_value=1, max_value=999)
    description = fake.sentence()
    checkout_url = (
        f"https://mollie.test/checkout/{fake.password(length=10,special_chars=False)}/"
    )

    data = {
        "id": transaction_id,
        "amount": {
            "currency": currency,
            "value": str(amount),
        },
        "status": "open",
        "description": description,
        "_links": {
            "checkout": {
                "href": checkout_url,
                "type": "text/html",
            },
        },
    }
    return Payment(data, None)
