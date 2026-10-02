"""Small, pure helper functions (easy to unit-test)."""
from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query parameters that only track marketing/referrals. Removing them lets us
# recognise the same article even when shared through different links.
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ocid", "ref", "cmpid", "ito", "from",
}


def normalize_url(url: str) -> str:
    """Canonical form of a URL so duplicates collapse to one value."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in TRACKING_PARAMS]
    query.sort()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def text_fingerprint(text: str) -> str:
    """Hash of the text ignoring case and whitespace, to detect identical bodies."""
    return sha1(re.sub(r"\s+", " ", text.lower()).strip())


class _TagStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def clean_html(text: str | None) -> str:
    """Remove HTML tags and collapse whitespace (RSS summaries often contain HTML)."""
    if not text:
        return ""
    stripper = _TagStripper()
    stripper.feed(text)
    stripper.close()
    return re.sub(r"\s+", " ", "".join(stripper.parts)).strip()


def parse_datetime(value) -> str | None:
    """Turn the many date formats we meet into one ISO-8601 UTC string.

    Accepts: time.struct_time (feedparser), RFC-2822 strings (RSS),
    ISO strings (APIs), and GDELT's 20260101T120000Z format.
    """
    if value is None or value == "":
        return None
    try:
        if isinstance(value, time.struct_time):
            dt = datetime(*value[:6], tzinfo=timezone.utc)
        else:
            s = str(value).strip()
            if re.fullmatch(r"\d{8}T\d{6}Z", s):
                dt = datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            else:
                try:
                    dt = parsedate_to_datetime(s)
                except (TypeError, ValueError):
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError):
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
