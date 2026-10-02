import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsintel.collectors import db, fulltext
from newsintel.collectors.models import Article


class FakeResponse:
    def __init__(self, text="", status=200):
        self.text, self.status_code = text, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Serves canned responses by URL substring; records requests."""

    def __init__(self, routes):
        self.routes, self.requested = routes, []

    def get(self, url, **kwargs):
        self.requested.append(url)
        for key, resp in self.routes.items():
            if key in url:
                return resp
        return FakeResponse("", 404)


ROBOTS_BLOCK = FakeResponse("User-agent: *\nDisallow: /private/\n")


class RobotsTests(unittest.TestCase):
    def test_disallowed_path_blocked(self):
        robots = fulltext.RobotsCache(FakeSession({"robots.txt": ROBOTS_BLOCK}))
        self.assertFalse(robots.allowed("https://s.com/private/a"))
        self.assertTrue(robots.allowed("https://s.com/public/a"))

    def test_missing_robots_allows(self):
        robots = fulltext.RobotsCache(FakeSession({"robots.txt": FakeResponse("", 404)}))
        self.assertTrue(robots.allowed("https://s.com/a"))

    def test_forbidden_robots_blocks(self):
        robots = fulltext.RobotsCache(FakeSession({"robots.txt": FakeResponse("", 403)}))
        self.assertFalse(robots.allowed("https://s.com/a"))


class ProcessTests(unittest.TestCase):
    def _run(self, page_resp, extracted):
        session = FakeSession({"robots.txt": FakeResponse("", 404), "s.com/a": page_resp})
        with mock.patch.object(fulltext, "extract_text", return_value=extracted):
            return fulltext.process_one("https://s.com/a", session, fulltext.RobotsCache(session))

    def test_ok(self):
        _text, status, err = self._run(FakeResponse("<html/>"), "x" * 500)
        self.assertEqual((status, err), ("ok", None))

    def test_too_short(self):
        self.assertEqual(self._run(FakeResponse("<html/>"), "tiny")[1], "too_short")

    def test_http_error_marked_failed(self):
        self.assertEqual(self._run(FakeResponse("", 500), None)[1], "failed")

    def test_robots_block_means_no_page_request(self):
        session = FakeSession({"robots.txt": ROBOTS_BLOCK})
        status = fulltext.process_one("https://s.com/private/a", session, fulltext.RobotsCache(session))[1]
        self.assertEqual(status, "blocked_robots")
        self.assertFalse(any("private" in u for u in session.requested))

    def test_run_updates_database(self):
        conn = db.connect(":memory:")
        db.init_db(conn)
        db.insert_article(conn, Article("rss", "o", "en", "https://s.com/a", "T"))
        session = FakeSession({"robots.txt": FakeResponse("", 404), "s.com/a": FakeResponse("<html/>")})
        with mock.patch.object(fulltext, "extract_text", return_value="word " * 200):
            counts = fulltext.run(conn, session, limit=10)
        self.assertEqual(counts, {"ok": 1})
        self.assertEqual(db.stats(conn)["by_status"], [("ok", 1)])


if __name__ == "__main__":
    unittest.main()
