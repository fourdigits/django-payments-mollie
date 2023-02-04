# The sandbox application

The sandbox is a simple as possible example, implementing `django-payments-mollie` in a django app.

To start using it, you have to take some simple steps:

- Login at Mollie and get a (test) API key from the dashboard, make sure to enable one or more payment methods
- Install `django-payments-mollie` in your virtualenv: pip install `django-payments-mollie`
- Run [localtunnel](https://github.com/localtunnel/localtunnel), [ngrok](https://ngrok.com/) or a similar tool and expose the Django runserver interface at `localhost:8000`: `lt --port 8000`
- Set the environment variable `MOLLIE_API_KEY` to your API key: `export MOLLIE_API_KEY=test_123...`
- Set the environment variable `PAYMENT_HOST` to your tunnel URL (without the `https://` scheme): `export PAYMENT_HOST=some-random-prefix.loca.lt`
- Start the sandbox app: `python manage.py migrate; python manage.py runserver`
- Start a payment flow at http://localhost:8000/create-payment/
