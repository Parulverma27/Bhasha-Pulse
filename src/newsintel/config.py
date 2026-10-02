"""Central configuration.

Every other module reads settings from here instead of calling os.environ
directly. That keeps secrets and paths in one place and makes testing easy.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Project root = two levels above this file's package (src/newsintel/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ANNOTATIONS_DIR = DATA_DIR / "annotations"
CONFIG_DIR = PROJECT_ROOT / "config"

SUPPORTED_LANGUAGES = ("en", "hi")


@dataclass(frozen=True)
class Outlet:
    id: str
    name: str
    language: str
    rss: str
    verified: bool = False
    notes: str = ""


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///data/newsintel.sqlite"
    log_level: str = "INFO"
    backend_port: int = 8000
    allowed_origins: tuple[str, ...] = ("http://localhost:3000",)
    gnews_api_key: str = ""
    newsdata_api_key: str = ""
    hf_token: str = ""
    outlets: list[Outlet] = field(default_factory=list)


def load_outlets(path: Path | None = None) -> list[Outlet]:
    """Read config/outlets.yaml and validate each entry."""
    path = path or CONFIG_DIR / "outlets.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    outlets: list[Outlet] = []
    seen: set[str] = set()
    for item in raw.get("outlets", []):
        outlet = Outlet(
            id=item["id"],
            name=item["name"],
            language=item["language"],
            rss=item["rss"],
            verified=bool(item.get("verified", False)),
            notes=item.get("notes", ""),
        )
        if outlet.language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Outlet '{outlet.id}' has unsupported language '{outlet.language}'. "
                f"Use one of {SUPPORTED_LANGUAGES}."
            )
        if outlet.id in seen:
            raise ValueError(f"Duplicate outlet id: '{outlet.id}'")
        seen.add(outlet.id)
        outlets.append(outlet)
    return outlets


def get_settings() -> Settings:
    """Build a Settings object from environment variables and outlets.yaml."""
    origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/newsintel.sqlite"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        gnews_api_key=os.getenv("GNEWS_API_KEY", ""),
        newsdata_api_key=os.getenv("NEWSDATA_API_KEY", ""),
        hf_token=os.getenv("HF_TOKEN", ""),
        outlets=load_outlets(),
    )
