import logging
from typing import Dict, Optional

# use the local overriding one
from synthetic_third_party_local_override import ThirdPartySyntheticTestsService

from dynatrace.http_client import HttpClient


class Dynatrace:
    def __init__(
        self,
        base_url: str,
        token: str,
        log: logging.Logger = None,
        proxies: Dict = None,
        too_many_requests_strategy=None,
        retries: int = 0,
        retry_delay_ms: int = 0,
        mc_jsession_id: Optional[str] = None,
        mc_b925d32c: Optional[str] = None,
        mc_sso_csrf_cookie: Optional[str] = None,
    ):
        self.__http_client = HttpClient(
            base_url, token, log, proxies, too_many_requests_strategy, retries, retry_delay_ms, mc_jsession_id, mc_b925d32c, mc_sso_csrf_cookie,
        )

        self.third_part_synthetic_tests: ThirdPartySyntheticTestsService = ThirdPartySyntheticTestsService(self.__http_client)
