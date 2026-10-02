"""Full-text extraction.

For each article still marked 'pending' we: check robots.txt, download the page
politely, and extract the main article text with trafilatura (which removes
menus, ads and comments).

text_status values:
  pending         not tried yet
  ok              text extracted
  too_short       page fetched but extracted text was tiny (paywall / video page)
  blocked_robots  robots.txt disallows us (we respect it)
  failed          download or extraction error (see fetch_error)
"""
from __future__ import annotations

import logging
import sqlite3
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from . import db
from .http import PoliteSession, user_agent

log = logging.getLogger(__name__)

MIN_CHARS = 300  # shorter than this is almost certainly not a real article body


class RobotsCache:
    """Fetches and caches robots.txt once per host."""

    def __init__(self, session: PoliteSession) -> None:
        self.session = session
        self._cache: dict[str, RobotFileParser | None] = {}

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._cache:
            self._cache[host] = self._load(host)
        rp = self._cache[host]
        return True if rp is None else rp.can_fetch(user_agent(), url)

    def _load(self, host: str) -> RobotFileParser | None:
        rp = RobotFileParser()
        try:
            resp = self.session.get(f"{host}/robots.txt")
        except Exception as exc:  # noqa: BLE001
            log.warning("robots.txt unreachable for %s (%s); skipping host to be safe", host, exc)
            rp.disallow_all = True
            return rp
        if resp.status_code in (401, 403):
            rp.disallow_all = True
            return rp
        if resp.status_code >= 400:
            return None  # no robots.txt -> everything allowed
        rp.parse(resp.text.splitlines())
        return rp


def extract_text(html: str, url: str) -> str | None:
    import trafilatura  # imported here so other modules/tests work without it

    return trafilatura.extract(
        html, url=url, include_comments=False, include_tables=False, favor_precision=True
    )


def process_one(url: str, session: PoliteSession, robots: RobotsCache) -> tuple[str | None, str, str | None]:
    """Returns (text, status, error)."""
    if not robots.allowed(url):
        return None, "blocked_robots", None
    try:
        resp = session.get(url)
        resp.raise_for_status()
        text = extract_text(resp.text, url)
    except Exception as exc:  # noqa: BLE001
        return None, "failed", str(exc)[:300]
    if not text:
        return None, "failed", "no article text extracted"
    if len(text) < MIN_CHARS:
        return text, "too_short", None
    return text, "ok", None


def run(conn: sqlite3.Connection, session: PoliteSession, limit: int = 100,
        language: str | None = None) -> dict[str, int]:
    robots = RobotsCache(session)
    counts: dict[str, int] = {}
    for row in db.pending_fulltext(conn, limit, language):
        text, status, error = process_one(row["url"], session, robots)
        db.save_fulltext(conn, row["id"], text, status, error)
        conn.commit()
        counts[status] = counts.get(status, 0) + 1
        log.info("fulltext #%d %s -> %s", row["id"], row["outlet_id"], status)
    return counts
