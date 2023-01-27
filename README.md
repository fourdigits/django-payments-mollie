# django-payments-mollie

[![PyPI - Version](https://img.shields.io/pypi/v/django-payments-mollie.svg)](https://pypi.org/project/django-payments-mollie)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-payments-mollie.svg)](https://pypi.org/project/django-payments-mollie)

-----

Django Payments Mollie is a Django app that adds support for the [Mollie payment provider](https://www.mollie.com) to [Django Payments](https://django-payments.readthedocs.io/).

**Table of Contents**

- [Installation](#installation)
- [Configuration](#configuration)
- [License](#license)

## Installation

```console
pip install django-payments-mollie
```

## Configuration

You should follow the configration guide in the Django Payments documentation. To setup this package as a payment variant, use the following `PAYMENT_VARIANTS` in the Django settings file:

```python
PAYMENT_VARIANTS = {
    "mollie": (
        "django_payments_mollie.provider.MollieProvider",
        {
            # For api key authentication
            "api_key": "test_example-api-key",

            # For access token authentication
            "access_token": "access_example-token",
            "testmode": True,

            # For OAuth2 authentication
            "client_id": "example-client-id",
            "client_secret": "example-client-secret",
            "testmode": True,
        }
    )
}
```

### Available configuration options

- `api_key`: A [Mollie API key](https://docs.mollie.com/overview/authentication#creating-api-keys), this is the simplest way to configure access to the Mollie API. Use the test key for development or testing. This also allows you to use payment methods that aren't enabled for live payments yet.

### Configuration helpers

#### Payment model

Django Payments docs will instruct you to create a Payment model that subclasses `BasePayment`. This package also provides a base model that you can use (optionally). The abstract model class `BaseMolliePayment` is a subclass of `BasePayment`, and it configures some of the fields as `required=True`, since Mollie requires them to be filled. Use it just like you would use Django payments' `BasePayment`:

```python
from django_mollie_payments.models import BaseMolliePayment

class Payment(BaseMolliePayment):
    ...
    # Add custom fields and methods
```


## License

`django-payments-mollie` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
