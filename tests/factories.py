import factory
from factory.django import DjangoModelFactory
from payments import PaymentStatus, get_payment_model

from tests.test_app.models import BaseMolliePayment


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = get_payment_model()

    total = factory.Faker("pydecimal", min_value=1, max_value=99999, right_digits=2)
    currency = factory.Faker("currency_code")
    description = factory.Faker("sentence")

    class Params:
        submitted = factory.Trait(
            status=PaymentStatus.INPUT,
            transaction_id="tr_12345",
        )
