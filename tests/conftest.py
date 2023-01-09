import json
from functools import partialmethod
from pathlib import Path

import pytest
import responses as responses_lib


class RequestsMock(responses_lib.RequestsMock):
    def add(
        self,
        method=None,
        url=None,
        body="",
        adding_headers=None,
        *args,
        **kwargs,
    ):
        """
        Add support for some shortcuts that we use a lot

        Allow the `mock_json` argument to receive a filename for a mock
        response from the `mock_reponses` directory.
        """
        mock_json = kwargs.pop("mock_json", None)
        if mock_json:
            file = (
                Path(__file__).resolve().parent / "mock_responses" / f"{mock_json}.json"
            )
            with file.open() as fh:
                payload = json.load(fh)
                kwargs["json"] = payload

        return super().add(method, url, body, adding_headers, *args, **kwargs)

    delete = partialmethod(add, "DELETE")
    get = partialmethod(add, "GET")
    head = partialmethod(add, "HEAD")
    options = partialmethod(add, "OPTIONS")
    patch = partialmethod(add, "PATCH")
    post = partialmethod(add, "POST")
    put = partialmethod(add, "PUT")


@pytest.fixture
def responses():
    with RequestsMock() as rsps:
        yield rsps
