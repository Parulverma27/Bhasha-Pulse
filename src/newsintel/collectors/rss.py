"""RSS collector.

RSS gives us headline, summary, link and date, but usually NOT the full text.
Full text is fetched separately (fulltext.py).
"""
from __future__ import annotations

import logging
import sqlite3
from html.parser import HTMLParser

from newsintel.config import Outlet

from . import db
from .http import PoliteSession
from .models import Article
from .utils import clean_html, normalize_url, parse_datetime

log = logging.getLogger(__name__)


def entries_to_articles(entries, outlet: Outlet) -> list[Article]:
    """Convert feedparser entries (dict-like) into Article objects."""
    articles: list[Article] = []
    for e in entries:
        link = e.get("link")
        title = clean_html(e.get("title"))
        if not link or not title:
            continue
        published = e.get("published_parsed") or e.get("updated_parsed") \
            or e.get("published") or e.get("updated")
        articles.append(Article(
            source_type="rss",
            outlet_id=outlet.id,
            language=outlet.language,
            url=normalize_url(link),
            title=title,
            summary=clean_html(e.get("summary") or e.get("description")),
            published_at=parse_datetime(published),
        ))
    return articles


def fetch_feed_entries(url: str, session: PoliteSession) -> list:
    import feedparser  # imported here so tests can run without it

    resp = session.get(url)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"Could not parse feed: {parsed.bozo_exception}")
    return parsed.entries


def collect_outlet(conn: sqlite3.Connection, outlet: Outlet,
                   session: PoliteSession) -> tuple[int, int]:
    """Collect one outlet. Returns (articles_seen, articles_inserted)."""
    entries = fetch_feed_entries(outlet.rss, session)
    articles = entries_to_articles(entries, outlet)
    inserted = sum(db.insert_article(conn, a) for a in articles)
    conn.commit()
    log.info("%s: %d seen, %d new", outlet.id, len(articles), inserted)
    return len(articles), inserted


def collect_all(conn: sqlite3.Connection, outlets: list[Outlet],
                session: PoliteSession) -> None:
    total_seen = total_new = errors = 0
    for outlet in outlets:
        try:
            seen, new = collect_outlet(conn, outlet, session)
            total_seen += seen
            total_new += new
        except Exception as exc:  # noqa: BLE001 - one bad feed must not stop the rest
            errors += 1
            log.warning("%s failed: %s", outlet.id, exc)
    db.log_run(conn, "rss", total_seen, total_new, errors)
    conn.commit()


# ---- Helpers for finding / checking feeds -------------------------------------------

class _FeedLinkFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.feeds: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = dict(attrs)
        if "alternate" in (a.get("rel") or "") and (a.get("type") or "") in (
            "application/rss+xml", "application/atom+xml"
        ) and a.get("href"):
            self.feeds.append(a["href"])


def discover_feeds(page_url: str, session: PoliteSession) -> list[str]:
    """Look in a web page's <head> for advertised RSS/Atom feeds."""
    from urllib.parse import urljoin

    resp = session.get(page_url)
    resp.raise_for_status()
    finder = _FeedLinkFinder()
    finder.feed(resp.text)
    return [urljoin(page_url, href) for href in finder.feeds]


def check_outlet(outlet: Outlet, session: PoliteSession) -> tuple[bool, str]:
    """Used by `verify-outlets`: does this feed return usable articles?"""
    try:
        entries = fetch_feed_entries(outlet.rss, session)
        arts = entries_to_articles(entries, outlet)
        if not arts:
            return False, "feed parsed but contained no usable entries"
        newest = max((a.published_at for a in arts if a.published_at), default="unknown")
        return True, f"{len(arts)} entries, newest: {newest}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
