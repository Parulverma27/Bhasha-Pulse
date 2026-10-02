"""GDELT DOC 2.0 collector (free, no key).

GDELT returns metadata only (url, title, date, domain, language), so articles
found this way also go through the full-text step.
Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
NOTE: verify the parameter names against the docs when you first run it.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

import yaml

from newsintel.config import CONFIG_DIR

from . import db
from .http import PoliteSession
from .models import Article
from .utils import normalize_url, parse_datetime

log = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_LANG_NAMES = {"en": "english", "hi": "hindi"}
GDELT_LANG_CODES = {"english": "en", "hindi": "hi"}
GDELT_MIN_INTERVAL = 6  # seconds between requests (GDELT asks for ~1 per 5 s)


def load_queries(path: Path | None = None) -> dict[str, list[str]]:
    path = path or CONFIG_DIR / "gdelt_queries.yaml"
    with open(path, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("queries", {})


def build_query(keyword: str, language: str, country: str = "IN") -> str:
    return f'"{keyword}" sourcecountry:{country} sourcelang:{GDELT_LANG_NAMES[language]}'


def parse_response(data: dict) -> list[Article]:
    articles: list[Article] = []
    for item in data.get("articles", []):
        url, title = item.get("url"), (item.get("title") or "").strip()
        if not url or not title:
            continue
        lang = GDELT_LANG_CODES.get((item.get("language") or "").lower(), "unknown")
        articles.append(Article(
            source_type="gdelt",
            outlet_id=item.get("domain") or "unknown",
            language=lang,
            url=normalize_url(url),
            title=title,
            published_at=parse_datetime(item.get("seendate")),
        ))
    return articles


RETRY_DELAYS = (30, 60, 120)


def fetch(keyword: str, language: str, session: PoliteSession,
          timespan: str = "1d", max_records: int = 100,
          sleep_fn=time.sleep) -> list[Article]:
    params = {
        "query": build_query(keyword, language),
        "mode": "artlist",
        "format": "json",
        "maxrecords": max_records,
        "timespan": timespan,
        "sort": "datedesc",
    }
    for delay in RETRY_DELAYS:
        resp = session.get(GDELT_DOC_API, params=params)
        if resp.status_code == 429:
            sleep_fn(delay)
            continue
        break
    else:
        resp = session.get(GDELT_DOC_API, params=params)
        if resp.status_code == 429:
            if hasattr(resp, "raise_for_status"):
                resp.raise_for_status()
            raise RuntimeError(f"GDELT rate limit (429) for keyword '{keyword}' after retries")

    if hasattr(resp, "raise_for_status"):
        resp.raise_for_status()

    if "too short" in (resp.text or "").lower():
        raise ValueError(f"GDELT query '{keyword}' is too short")

    try:
        return parse_response(resp.json())
    except ValueError as exc:  # GDELT sometimes returns plain-text errors
        raise ValueError(f"GDELT returned non-JSON: {resp.text[:120]!r}") from exc


def collect(conn: sqlite3.Connection, session: PoliteSession, timespan: str = "1d",
            max_records: int = 100, sleep_fn=time.sleep) -> None:
    seen = new = errors = 0
    for language, keywords in load_queries().items():
        for kw in keywords:
            try:
                arts = fetch(kw, language, session, timespan, max_records, sleep_fn=sleep_fn)
                seen += len(arts)
                new += sum(db.insert_article(conn, a) for a in arts)
                conn.commit()
                log.info("gdelt [%s] %r: %d seen", language, kw, len(arts))
            except Exception as exc:  # noqa: BLE001
                errors += 1
                log.warning("gdelt [%s] %r failed: %s", language, kw, exc)
            sleep_fn(GDELT_MIN_INTERVAL)
    db.log_run(conn, "gdelt", seen, new, errors)
    conn.commit()
