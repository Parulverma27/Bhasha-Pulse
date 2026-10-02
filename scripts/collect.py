"""Command-line entry point for data collection.

Examples (run from the project root, with your virtual environment active):

    python scripts/collect.py init-db
    python scripts/collect.py verify-outlets
    python scripts/collect.py discover-feed https://www.example.com
    python scripts/collect.py rss                 # verified outlets only
    python scripts/collect.py rss --include-unverified
    python scripts/collect.py gdelt --timespan 1d
    python scripts/collect.py gnews
    python scripts/collect.py fulltext --limit 100
    python scripts/collect.py run-all             # rss + gdelt + (gnews if key) + fulltext
    python scripts/collect.py stats
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsintel.collectors import db, filters, fulltext, gdelt, gnews, rss
from newsintel.collectors.http import PoliteSession
from newsintel.config import get_settings
from newsintel.logging_setup import setup_logging

log = logging.getLogger("collect")


def selected_outlets(include_unverified: bool):
    outlets = get_settings().outlets
    chosen = [o for o in outlets if include_unverified or o.verified]
    if not chosen:
        log.warning(
            "No verified outlets. Run `verify-outlets`, set verified: true in "
            "config/outlets.yaml for working feeds, or pass --include-unverified."
        )
    return chosen


def cmd_init_db(args) -> None:
    with db.connect() as conn:
        db.init_db(conn)
    print("Database ready.")


def cmd_verify(args) -> None:
    session = PoliteSession()
    print(f"{'outlet':<22}{'lang':<6}result")
    for o in get_settings().outlets:
        ok, msg = rss.check_outlet(o, session)
        print(f"{o.id:<22}{o.language:<6}{'OK  ' if ok else 'FAIL'} {msg}")
    print("\nSet `verified: true` in config/outlets.yaml for every OK outlet.")


def cmd_discover(args) -> None:
    feeds = rss.discover_feeds(args.url, PoliteSession())
    print("\n".join(feeds) if feeds else "No feeds advertised on that page. Try /rss, /feed or a site 'RSS' page.")


def cmd_rss(args) -> None:
    with db.connect() as conn:
        db.init_db(conn)
        rss.collect_all(conn, selected_outlets(args.include_unverified), PoliteSession())


def cmd_gdelt(args) -> None:
    with db.connect() as conn:
        db.init_db(conn)
        gdelt.collect(conn, PoliteSession(delay=1), args.timespan, args.max_records)


def cmd_gnews(args) -> None:
    with db.connect() as conn:
        db.init_db(conn)
        gnews.collect(conn, PoliteSession(delay=1))


def cmd_fulltext(args) -> None:
    with db.connect() as conn:
        db.init_db(conn)
        counts = fulltext.run(conn, PoliteSession(), args.limit, args.language)
    print("Full-text results:", counts or "nothing pending")


def cmd_run_all(args) -> None:
    with db.connect() as conn:
        db.init_db(conn)
        rss.collect_all(conn, selected_outlets(args.include_unverified), PoliteSession())
        if not args.skip_gdelt:
            gdelt.collect(conn, PoliteSession(delay=1), "1d", 100)
        if os.getenv("GNEWS_API_KEY"):
            gnews.collect(conn, PoliteSession(delay=1))
        counts = fulltext.run(conn, PoliteSession(), args.fulltext_limit)
        print("Full-text results:", counts or "nothing pending")


def cmd_stats(args) -> None:
    with db.connect() as conn:
        db.init_db(conn)
        s = db.stats(conn)
    print(f"Total articles: {s['total']}   (exact-duplicate bodies: {s['duplicates']})")
    print(f"Date range:     {s['date_range'][0]}  ->  {s['date_range'][1]}")
    print("By language:   ", dict(s["by_language"]))
    print("Text status:   ", dict(s["by_status"]))
    print("By outlet:")
    for outlet, lang, n in s["by_outlet"]:
        print(f"  {outlet:<28}{lang:<8}{n}")


def cmd_purge_blocked(args) -> None:
    blocked = filters.load_blocked_domains()
    with db.connect() as conn:
        db.init_db(conn)
        count = db.purge_blocked_articles(conn, blocked, apply=args.apply)
    if args.apply:
        print(f"Purged {count} blocked rows.")
    else:
        print(f"Dry run: {count} blocked rows would be deleted (run with --apply to delete).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db").set_defaults(func=cmd_init_db)
    sub.add_parser("verify-outlets").set_defaults(func=cmd_verify)
    p = sub.add_parser("discover-feed"); p.add_argument("url"); p.set_defaults(func=cmd_discover)
    p = sub.add_parser("rss"); p.add_argument("--include-unverified", action="store_true"); p.set_defaults(func=cmd_rss)
    p = sub.add_parser("gdelt"); p.add_argument("--timespan", default="1d"); p.add_argument("--max-records", type=int, default=100); p.set_defaults(func=cmd_gdelt)
    sub.add_parser("gnews").set_defaults(func=cmd_gnews)
    p = sub.add_parser("fulltext"); p.add_argument("--limit", type=int, default=100); p.add_argument("--language", choices=["en", "hi"]); p.set_defaults(func=cmd_fulltext)
    p = sub.add_parser("run-all"); p.add_argument("--include-unverified", action="store_true"); p.add_argument("--skip-gdelt", action="store_true"); p.add_argument("--fulltext-limit", type=int, default=200); p.set_defaults(func=cmd_run_all)
    sub.add_parser("stats").set_defaults(func=cmd_stats)
    p = sub.add_parser("purge-blocked")
    p.add_argument("--apply", action="store_true", help="Apply deletion of blocked articles")
    p.set_defaults(func=cmd_purge_blocked)

    args = parser.parse_args()
    setup_logging(get_settings().log_level)
    args.func(args)


if __name__ == "__main__":
    main()
