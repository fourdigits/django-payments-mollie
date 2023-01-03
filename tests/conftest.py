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

        Allow the `json` argument to receive a
        """
        json_kwarg = kwargs.get("json")
        if isinstance(json_kwarg, str):
            # Read a mocked_response file and use that as JSON body
            filename = json_kwarg
            file = (
                Path(__file__).resolve().parent / "mock_responses" / f"{filename}.json"
            )
            with file.open() as fh:
                payload = json.load(fh)
                kwargs["json"] = payload

        return super().add(method, url, body, adding_headers, *args, **kwargs)

    post = partialmethod(add, "POST")


@pytest.fixture
def responses():
    with RequestsMock() as rsps:
        yield rsps
