"""The one data structure every collector produces."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Article:
    source_type: str            # "rss" | "gdelt" | "gnews"
    outlet_id: str              # id from outlets.yaml, or the domain for gdelt/gnews
    language: str               # "en" | "hi" | "unknown"
    url: str                    # normalised URL (see utils.normalize_url)
    title: str
    summary: str = ""           # RSS description / API snippet (NOT the full text)
    published_at: str | None = None   # ISO-8601 UTC string, or None if unknown
