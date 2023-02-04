from payments.models import BasePayment

from django_payments_mollie.models import BaseMolliePayment


class MollieTestPayment(BaseMolliePayment):
    """Payment model subclassing the BaseMolliePayment model"""

    def get_failure_url(self):
        return "https://example.com/failure"

    def get_success_url(self):
        return "https://example.com/success"


class BaseTestPayment(BasePayment):
    """Payment model subclassing Django Payments' BaseModel"""

    def get_failure_url(self):
        return "https://example.com/failure"

    def get_success_url(self):
        return "https://example.com/success"
