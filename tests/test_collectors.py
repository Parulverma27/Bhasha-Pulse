import sqlite3
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsintel.collectors import db, gdelt, gnews
from newsintel.collectors.models import Article
from newsintel.collectors.rss import entries_to_articles
from newsintel.collectors.utils import (
    clean_html,
    normalize_url,
    parse_datetime,
    text_fingerprint,
)
from newsintel.config import Outlet


class UtilsTests(unittest.TestCase):
    def test_normalize_url_removes_tracking_and_fragment(self):
        a = normalize_url("HTTPS://Example.com/news/story/?utm_source=x&id=5#top")
        b = normalize_url("https://example.com/news/story?id=5")
        self.assertEqual(a, b)

    def test_normalize_url_keeps_root_path(self):
        self.assertEqual(normalize_url("https://example.com"), "https://example.com/")

    def test_clean_html(self):
        self.assertEqual(clean_html("<p>Hello  <b>world</b></p>\n"), "Hello world")
        self.assertEqual(clean_html(None), "")

    def test_parse_datetime_formats(self):
        self.assertEqual(parse_datetime("Wed, 01 Oct 2026 10:30:00 +0530"), "2026-10-01T05:00:00+00:00")
        self.assertEqual(parse_datetime("20261001T120000Z"), "2026-10-01T12:00:00+00:00")
        self.assertEqual(parse_datetime("2026-10-01T12:00:00Z"), "2026-10-01T12:00:00+00:00")
        self.assertEqual(parse_datetime(time.struct_time((2026, 10, 1, 12, 0, 0, 0, 0, 0))),
                         "2026-10-01T12:00:00+00:00")
        self.assertIsNone(parse_datetime("not a date"))
        self.assertIsNone(parse_datetime(None))

    def test_text_fingerprint_ignores_case_and_spacing(self):
        self.assertEqual(text_fingerprint("Hello   World"), text_fingerprint("hello world"))


class DbTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_db(self.conn)

    def _article(self, url="https://a.com/1", lang="en"):
        return Article("rss", "a", lang, url, "Title")

    def test_duplicate_url_not_inserted_twice(self):
        self.assertTrue(db.insert_article(self.conn, self._article()))
        self.assertFalse(db.insert_article(self.conn, self._article()))
        self.assertEqual(db.stats(self.conn)["total"], 1)

    def test_hindi_text_roundtrip(self):
        db.insert_article(self.conn, self._article(lang="hi"))
        row = db.pending_fulltext(self.conn, 10)[0]
        db.save_fulltext(self.conn, row["id"], "भारत की संसद में आज चर्चा हुई।", "ok")
        saved = self.conn.execute("SELECT full_text, word_count FROM articles").fetchone()
        self.assertEqual(saved["full_text"], "भारत की संसद में आज चर्चा हुई।")
        self.assertEqual(saved["word_count"], 7)

    def test_identical_body_flagged_as_duplicate(self):
        db.insert_article(self.conn, self._article("https://a.com/1"))
        db.insert_article(self.conn, self._article("https://b.com/2"))
        first, second = db.pending_fulltext(self.conn, 10)
        db.save_fulltext(self.conn, first["id"], "Same body text.", "ok")
        db.save_fulltext(self.conn, second["id"], "same  body TEXT.", "ok")
        dup = self.conn.execute("SELECT duplicate_of FROM articles WHERE id = ?", (second["id"],)).fetchone()
        self.assertEqual(dup["duplicate_of"], first["id"])
        self.assertEqual(db.stats(self.conn)["duplicates"], 1)

    def test_non_sqlite_url_rejected(self):
        with self.assertRaises(ValueError):
            db.db_path_from_url("postgresql://x")

    def test_fair_queue_spreads_outlets(self):
        from collections import Counter
        for o in ["out1", "out2", "out3"]:
            for i in range(5):
                db.insert_article(self.conn, Article("rss", o, "en", f"https://{o}.com/{i}", f"Title {i}"))
        rows = db.pending_fulltext(self.conn, limit=6)
        self.assertEqual(len(rows), 6)
        counts = Counter(r["outlet_id"] for r in rows)
        self.assertEqual(counts, {"out1": 2, "out2": 2, "out3": 2})


class ParserTests(unittest.TestCase):
    outlet = Outlet(id="test", name="Test", language="hi", rss="http://x")

    def test_rss_entries_converted(self):
        entries = [
            {"link": "https://t.com/a?utm_source=x", "title": "<b>शीर्षक</b>",
             "summary": "<p>सार</p>",
             "published_parsed": time.struct_time((2026, 10, 1, 12, 0, 0, 0, 0, 0))},
            {"link": "", "title": "no link is skipped"},
        ]
        arts = entries_to_articles(entries, self.outlet)
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0].url, "https://t.com/a")
        self.assertEqual(arts[0].title, "शीर्षक")
        self.assertEqual(arts[0].language, "hi")
        self.assertEqual(arts[0].published_at, "2026-10-01T12:00:00+00:00")

    def test_gdelt_response_parsed(self):
        data = {"articles": [
            {"url": "https://x.in/n1", "title": "Headline", "seendate": "20261001T080000Z",
             "domain": "x.in", "language": "Hindi", "sourcecountry": "India"},
            {"url": "", "title": "skipped"},
        ]}
        arts = gdelt.parse_response(data)
        self.assertEqual(len(arts), 1)
        self.assertEqual((arts[0].language, arts[0].outlet_id), ("hi", "x.in"))

    def test_gdelt_query_building(self):
        self.assertEqual(gdelt.build_query("India", "en"), '"India" sourcecountry:IN sourcelang:english')

    def test_gdelt_429_retry_then_success(self):
        class MockResp:
            def __init__(self, status_code, data=None):
                self.status_code = status_code
                self._data = data or {}
                self.text = ""

            def raise_for_status(self):
                pass

            def json(self):
                return self._data

        calls = [
            MockResp(429),
            MockResp(200, {"articles": [{"url": "https://a.in/1", "title": "T", "domain": "a.in", "language": "English", "seendate": "20261001T080000Z"}]}),
        ]

        class MockSession:
            def get(self, url, params=None):
                return calls.pop(0)

        slept = []
        arts = gdelt.fetch("India", "en", MockSession(), sleep_fn=slept.append)
        self.assertEqual(len(arts), 1)
        self.assertEqual(slept, [30])

    def test_gdelt_429_four_times_raises(self):
        class MockResp:
            status_code = 429
            text = "Too Many Requests"

            def raise_for_status(self):
                raise RuntimeError("429 error")

        class MockSession:
            def get(self, url, params=None):
                return MockResp()

        slept = []
        with self.assertRaises(RuntimeError):
            gdelt.fetch("India", "en", MockSession(), sleep_fn=slept.append)
        self.assertEqual(slept, [30, 60, 120])

    def test_gdelt_too_short_raises_value_error(self):
        class MockResp:
            status_code = 200
            text = "The specified phrase is too short.\n"

            def raise_for_status(self):
                pass

        class MockSession:
            def get(self, url, params=None):
                return MockResp()

        with self.assertRaises(ValueError) as ctx:
            gdelt.fetch("भारत", "hi", MockSession(), sleep_fn=lambda _: None)
        self.assertIn("भारत", str(ctx.exception))

    def test_gnews_response_parsed(self):
        data = {"articles": [{"url": "https://s.com/a", "title": "T", "description": "<i>d</i>",
                              "publishedAt": "2026-10-01T10:00:00Z",
                              "source": {"name": "S", "url": "https://s.com"}}]}
        arts = gnews.parse_response(data, "en")
        self.assertEqual((arts[0].outlet_id, arts[0].summary), ("s.com", "d"))

    def test_gnews_requires_key(self):
        import os
        os.environ.pop("GNEWS_API_KEY", None)
        with self.assertRaises(RuntimeError):
            gnews.collect(sqlite3.connect(":memory:"), None)


if __name__ == "__main__":
    unittest.main()
