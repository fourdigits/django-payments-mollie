from django.urls import reverse

from django_payments_mollie.models import BaseMolliePayment


class Payment(BaseMolliePayment):
    def get_failure_url(self):
        return reverse("payment-failure", kwargs={"payment_id": self.id})

    def get_success_url(self):
        return reverse("payment-success", kwargs={"payment_id": self.id})

    def get_purchased_items(self):
        # We don't use this (yet)
        raise NotImplementedError
