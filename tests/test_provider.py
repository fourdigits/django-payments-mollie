from payments.core import provider_factory


def test_get_provider_from_settings():
    provider = provider_factory("mollie")

    assert provider.client is not None, "Internal mollie client is unavailable"
    assert provider.testmode is True, "Testmode is not adopted correctly"
