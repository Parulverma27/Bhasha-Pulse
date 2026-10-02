from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml

from newsintel.config import CONFIG_DIR


def load_blocked_domains(path: Path | None = None) -> set[str]:
    path = path or CONFIG_DIR / "blocked_domains.yaml"
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {d.strip().lower() for d in data.get("domains", []) if d and d.strip()}


def is_blocked(url: str, blocked: set[str] | list[str]) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return False
    blocked_set = {d.lower() for d in blocked}
    for b in blocked_set:
        if host == b or host.endswith(f".{b}"):
            return True
    return False
