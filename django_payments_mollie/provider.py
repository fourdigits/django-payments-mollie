from typing import Optional

from mollie.api.client import Client as MollieClient
from payments.core import BasicProvider


class MollieProvider(BasicProvider):
    """
    Django-payments provider class for Mollie.
    """

    client: MollieClient
    testmode: bool
    capture: bool

    def __init__(
        self,
        token: Optional[str] = None,
        testmode: bool = False,
        capture: bool = False,
    ):
        self.client = MollieClient()
        self.testmode = testmode
        self.capture = capture
