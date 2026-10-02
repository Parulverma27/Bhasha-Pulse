"""SQLite storage layer.

We use SQLite now because it needs no setup. All SQL lives in this file, so
when we move to PostgreSQL (Milestone 7/9) only this file has to change.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from newsintel.config import PROJECT_ROOT, get_settings

from .models import Article
from .utils import sha1, text_fingerprint, utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type     TEXT NOT NULL,
    outlet_id       TEXT NOT NULL,
    language        TEXT NOT NULL,
    url             TEXT NOT NULL,
    url_hash        TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    summary         TEXT DEFAULT '',
    published_at    TEXT,
    collected_at    TEXT NOT NULL,
    full_text       TEXT,
    text_hash       TEXT,
    word_count      INTEGER,
    text_status     TEXT NOT NULL DEFAULT 'pending',
    fetch_error     TEXT,
    duplicate_of    INTEGER REFERENCES articles(id)
);
CREATE INDEX IF NOT EXISTS idx_articles_status   ON articles(text_status);
CREATE INDEX IF NOT EXISTS idx_articles_outlet   ON articles(outlet_id);
CREATE INDEX IF NOT EXISTS idx_articles_lang     ON articles(language);
CREATE INDEX IF NOT EXISTS idx_articles_text_hash ON articles(text_hash);

CREATE TABLE IF NOT EXISTS collection_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    source      TEXT NOT NULL,
    seen        INTEGER NOT NULL,
    inserted    INTEGER NOT NULL,
    errors      INTEGER NOT NULL DEFAULT 0,
    note        TEXT
);
"""


def db_path_from_url(url: str) -> Path:
    """sqlite:///data/newsintel.sqlite -> <project>/data/newsintel.sqlite"""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError(
            f"Only sqlite URLs are supported until Milestone 7 (got '{url}')."
        )
    path = Path(url[len(prefix):])
    return path if path.is_absolute() else PROJECT_ROOT / path


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path) if path else db_path_from_url(get_settings().database_url)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def insert_article(conn: sqlite3.Connection, a: Article) -> bool:
    """Insert one article. Returns False if we already have this URL."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO articles
           (source_type, outlet_id, language, url, url_hash, title, summary,
            published_at, collected_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (a.source_type, a.outlet_id, a.language, a.url, sha1(a.url), a.title,
         a.summary, a.published_at, utc_now()),
    )
    return cur.rowcount == 1


def pending_fulltext(conn: sqlite3.Connection, limit: int,
                     language: str | None = None) -> list[sqlite3.Row]:
    where = "WHERE text_status = 'pending'"
    params: list = []
    if language:
        where += " AND language = ?"
        params.append(language)
    sql = f"""WITH ranked AS (
        SELECT id, url, outlet_id,
               ROW_NUMBER() OVER (PARTITION BY outlet_id ORDER BY id DESC) as rn
        FROM articles
        {where}
    )
    SELECT id, url, outlet_id FROM ranked ORDER BY rn, outlet_id LIMIT ?"""
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def save_fulltext(conn: sqlite3.Connection, article_id: int, text: str | None,
                  status: str, error: str | None = None) -> None:
    """Store extracted text (or a failure status) and flag exact-duplicate bodies."""
    text_hash = word_count = duplicate_of = None
    if text:
        text_hash = text_fingerprint(text)
        word_count = len(text.split())
        row = conn.execute(
            "SELECT id FROM articles WHERE text_hash = ? AND id != ? ORDER BY id LIMIT 1",
            (text_hash, article_id),
        ).fetchone()
        duplicate_of = row["id"] if row else None
    conn.execute(
        """UPDATE articles SET full_text = ?, text_hash = ?, word_count = ?,
           text_status = ?, fetch_error = ?, duplicate_of = ? WHERE id = ?""",
        (text, text_hash, word_count, status, error, duplicate_of, article_id),
    )


def log_run(conn: sqlite3.Connection, source: str, seen: int, inserted: int,
            errors: int = 0, note: str = "") -> None:
    conn.execute(
        "INSERT INTO collection_runs (started_at, source, seen, inserted, errors, note)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (utc_now(), source, seen, inserted, errors, note),
    )


def stats(conn: sqlite3.Connection) -> dict:
    def rows(sql: str) -> list[tuple]:
        return [tuple(r) for r in conn.execute(sql).fetchall()]

    return {
        "total": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
        "by_language": rows("SELECT language, COUNT(*) FROM articles GROUP BY language"),
        "by_outlet": rows(
            "SELECT outlet_id, language, COUNT(*) FROM articles "
            "GROUP BY outlet_id, language ORDER BY COUNT(*) DESC"),
        "by_status": rows("SELECT text_status, COUNT(*) FROM articles GROUP BY text_status"),
        "duplicates": conn.execute(
            "SELECT COUNT(*) FROM articles WHERE duplicate_of IS NOT NULL").fetchone()[0],
        "date_range": tuple(conn.execute(
            "SELECT MIN(published_at), MAX(published_at) FROM articles").fetchone()),
    }
