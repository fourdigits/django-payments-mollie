from decimal import Decimal
from typing import Iterable

from payments import PurchasedItem
from payments.models import BasePayment


class Payment(BasePayment):
    def get_failure_url(self) -> str:
        return f"http://example.com/payments/{self.pk}/failure"

    def get_success_url(self) -> str:
        return f"http://example.com/payments/{self.pk}/success"

    def get_purchased_items(self) -> Iterable[PurchasedItem]:
        yield PurchasedItem(
            name="The Hound of the Baskervilles",
            sku="BSKV",
            quantity=9,
            price=Decimal(10),
            currency="USD",
        )
