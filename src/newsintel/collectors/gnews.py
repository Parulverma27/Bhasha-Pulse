"""GNews API collector (needs GNEWS_API_KEY in .env).

Free plans limit requests/day and may truncate article content, so we only use
this for headlines + URLs and fetch full text ourselves.
Docs: https://gnews.io/docs/v4   (verify parameter names and your plan's limits)
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from urllib.parse import urlsplit

from . import db
from .filters import is_blocked, load_blocked_domains
from .http import PoliteSession
from .models import Article
from .utils import clean_html, normalize_url, parse_datetime

log = logging.getLogger(__name__)

GNEWS_SEARCH = "https://gnews.io/api/v4/search"
DEFAULT_TOPICS = {"en": ["India politics", "India economy"], "hi": ["भारत राजनीति", "अर्थव्यवस्था"]}


def parse_response(data: dict, language: str) -> list[Article]:
    articles: list[Article] = []
    for item in data.get("articles", []):
        url, title = item.get("url"), (item.get("title") or "").strip()
        if not url or not title:
            continue
        source = item.get("source") or {}
        domain = urlsplit(source.get("url") or url).netloc or "unknown"
        articles.append(Article(
            source_type="gnews",
            outlet_id=domain,
            language=language,
            url=normalize_url(url),
            title=title,
            summary=clean_html(item.get("description")),
            published_at=parse_datetime(item.get("publishedAt")),
        ))
    return articles


def collect(conn: sqlite3.Connection, session: PoliteSession,
            topics: dict[str, list[str]] | None = None, max_per_query: int = 10) -> None:
    key = os.getenv("GNEWS_API_KEY", "")
    if not key:
        raise RuntimeError("GNEWS_API_KEY is empty. Add it to your .env file.")
    blocked = load_blocked_domains()
    seen = new = errors = 0
    for language, queries in (topics or DEFAULT_TOPICS).items():
        for q in queries:
            try:
                resp = session.get(GNEWS_SEARCH, params={
                    "q": q, "lang": language, "country": "in",
                    "max": max_per_query, "apikey": key,
                })
                resp.raise_for_status()
                arts = parse_response(resp.json(), language)
                seen += len(arts)
                arts = [a for a in arts if not is_blocked(a.url, blocked)]
                new += sum(db.insert_article(conn, a) for a in arts)
                conn.commit()
                log.info("gnews [%s] %r: %d seen", language, q, len(arts))
            except Exception as exc:  # noqa: BLE001
                errors += 1
                log.warning("gnews [%s] %r failed: %s", language, q, exc)
            time.sleep(1)
    db.log_run(conn, "gnews", seen, new, errors)
    conn.commit()
