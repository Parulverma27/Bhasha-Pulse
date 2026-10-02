import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsintel.config import get_settings, load_outlets


def _write(text: str) -> Path:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(text)
    return Path(f.name)


class ConfigTests(unittest.TestCase):
    def test_default_outlets_load(self):
        outlets = load_outlets()
        self.assertGreater(len(outlets), 0)
        self.assertTrue({o.language for o in outlets} <= {"en", "hi"})

    def test_settings_defaults(self):
        s = get_settings()
        self.assertTrue(s.database_url.startswith("sqlite"))
        self.assertIn("http://localhost:3000", s.allowed_origins)

    def test_bad_language_rejected(self):
        p = _write("outlets:\n  - {id: x, name: X, language: fr, rss: http://a}\n")
        with self.assertRaises(ValueError):
            load_outlets(p)

    def test_duplicate_id_rejected(self):
        p = _write(
            "outlets:\n"
            "  - {id: x, name: X, language: en, rss: http://a}\n"
            "  - {id: x, name: Y, language: hi, rss: http://b}\n"
        )
        with self.assertRaises(ValueError):
            load_outlets(p)


if __name__ == "__main__":
    unittest.main()
