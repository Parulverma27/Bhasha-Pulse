"""Polite HTTP: one place that sets the User-Agent, timeout and per-host delay."""
from __future__ import annotations

import os
import time
from urllib.parse import urlsplit

import requests

DEFAULT_UA = (
    "BhashaPulseBot/0.1 (student research project; "
    "set USER_AGENT in .env with your contact email)"
)


def user_agent() -> str:
    return os.getenv("USER_AGENT", DEFAULT_UA)


def request_delay() -> float:
    return float(os.getenv("REQUEST_DELAY_SECONDS", "2"))


class PoliteSession:
    """requests.Session that waits `delay` seconds between hits to the same host."""

    def __init__(self, delay: float | None = None, timeout: int = 20) -> None:
        self.delay = request_delay() if delay is None else delay
        self.timeout = timeout
        self._last_hit: dict[str, float] = {}
        self._session = requests.Session()
        self._session.headers["User-Agent"] = user_agent()

    def get(self, url: str, **kwargs) -> requests.Response:
        host = urlsplit(url).netloc
        wait = self.delay - (time.monotonic() - self._last_hit.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        try:
            return self._session.get(url, timeout=self.timeout, **kwargs)
        finally:
            self._last_hit[host] = time.monotonic()
