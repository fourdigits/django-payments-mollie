from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tests.test_app.models import MollieTestPayment

pytestmark = pytest.mark.django_db


def test_model_enforces_required_fields():
    with pytest.raises(ValidationError) as excinfo:
        MollieTestPayment.objects.create()

    assert excinfo.value.message_dict == {
        "total": ["Mollie requires 'total' to be set"],
        "currency": ["Mollie requires 'currency' to be set"],
        "description": ["Mollie requires 'description' to be set"],
    }


def test_model_allowes_save_with_nonempty_required_fields():
    payment = MollieTestPayment.objects.create(
        total=Decimal("13.37"),
        currency="EUR",
        description="My test payment",
    )

    assert payment.total == Decimal("13.37")
    assert payment.currency == "EUR"
    assert payment.description == "My test payment"


def test_model_ignores_explicit_not_updated_fields_during_save():
    payment = MollieTestPayment.objects.create(
        total=Decimal("13.37"),
        currency="OLD",
        description="My inital test payment",
    )

    payment.total = Decimal("0")
    payment.currency = "NEW"
    payment.description = "My updated payment description"

    with pytest.raises(ValidationError) as excinfo:
        payment.save()
    assert excinfo.value.messages == ["Mollie requires 'total' to be set"]

    # No error, 'total' field is ignored
    payment.save(update_fields=["description"])

    payment.refresh_from_db()
    assert payment.total == Decimal("13.37"), "Total should not have been updated"
    assert payment.currency == "OLD", "Currency was not in updated_fields, not saved"
    assert (
        payment.description == "My updated payment description"
    ), "Description is correct and should be updated"
