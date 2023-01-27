from decimal import Decimal
from typing import Any, List, Optional

from django.core.exceptions import ValidationError
from payments.models import BasePayment


class BaseMolliePayment(BasePayment):  # type: ignore[misc]
    """Abstract base model for Django Payments, targeted at Mollie transactions."""

    class Meta:
        abstract = True

    def validate_mollie_required_fields(
        self, update_fields: Optional[List[str]] = None
    ) -> None:
        """Validate all fields that Mollie requires."""
        required_fields = ["total", "currency", "description"]
        if update_fields:
            required_fields = [
                value for value in required_fields if value in update_fields
            ]

        errors = {}
        for field_name in required_fields:
            value = getattr(self, field_name)
            if not value or (field_name == "total" and not Decimal(value)):
                errors[field_name] = ValidationError(
                    f"Mollie requires '{field_name}' to be set", code="required"
                )

        if errors:
            raise ValidationError(errors)

    def save(
        self, *args: Any, update_fields: Optional[List[str]] = None, **kwargs: Any
    ) -> None:
        """Enforce validation of fields required by Mollie upon save."""
        self.validate_mollie_required_fields(update_fields)
        super().save(*args, update_fields=update_fields, **kwargs)
