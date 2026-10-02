# Milestone 1: Data Collection Pipeline

## What this milestone does
Builds the machinery that **collects news articles automatically** and stores them
in a database, so the dataset grows while you work on the rest of the project.

```
RSS feeds  ──┐
GDELT      ──┼─> Article objects ─> SQLite (url-deduplicated) ─> full-text step ─> ready for cleaning
GNews API  ──┘                                                   (robots.txt checked,
                                                                  trafilatura extracts text)
```

## New files (all under your repo root)
| File | What it does | Why |
|---|---|---|
| `src/newsintel/collectors/models.py` | `Article` dataclass | One common shape for data from every source |
| `.../utils.py` | URL normalising, HTML cleaning, date parsing, hashing | Pure functions, easy to test |
| `.../db.py` | SQLite schema + all SQL | All DB code in one file, so Postgres migration later touches only this |
| `.../http.py` | Polite HTTP session (User-Agent, delay per host) | Avoids hammering news sites |
| `.../rss.py` | RSS collector, feed discovery, feed checker | Main source of articles |
| `.../gdelt.py` | GDELT DOC API collector | Extra volume and history, free |
| `.../gnews.py` | GNews API collector (optional) | Adds API-based coverage |
| `.../fulltext.py` | robots.txt check + trafilatura text extraction | RSS rarely has the article body |
| `.../filters.py` | Domain blocklist filter for aggregators/non-news | Keeps non-news sites out |
| `scripts/collect.py` | Command-line tool for all of the above | The thing you actually run |
| `config/gdelt_queries.yaml` | Keywords for GDELT in English and Hindi | Editable without touching code |
| `config/blocked_domains.yaml` | Non-news domains to filter | Editable without touching code |
| `config/outlets.suggested.yaml` | Candidate outlets to verify and copy | Not used by code directly |
| `tests/test_collectors.py`, `tests/test_fulltext.py` | Unit tests | Offline: no internet needed |
| `docs/scheduling.md` | How to run it every few hours | Data needs calendar time |

## Milestone 1.1 Improvements
- **Fair Full-Text Queue (1a):** `pending_fulltext()` now uses a SQL window function (`ROW_NUMBER() OVER (PARTITION BY outlet_id ORDER BY id DESC)`) to distribute extraction evenly across outlets rather than starving later feeds in FIFO order.
- **GDELT Robustness (1b):** Added exponential backoff retry (30s, 60s, 120s) on HTTP 429 rate limit responses, explicit error handling for single-word / short phrase errors, and updated Hindi search terms to multi-word phrases (e.g. `भारत सरकार`, `लोकसभा चुनाव`, `संसद सत्र`).
- **Domain Blocklist (1c):** Added `config/blocked_domains.yaml` and `filters.py` to prevent non-news domains (e.g. `indiankanoon.org`, `prokerala.com`, `readersdigest.in`) from entering the collection, along with `python scripts/collect.py purge-blocked` to audit and purge existing pending rows.

## Key concepts (for your viva)
- **Why store `url_hash` UNIQUE:** the same article appears via RSS, GDELT and GNews. Normalising the URL (removing `utm_*` tracking, fragments, trailing slash) then hashing it lets the database reject repeats.
- **Two kinds of duplicates:** *same URL* (rejected at insert) and *same body under different URLs*, such as agency stories syndicated across outlets (flagged in `duplicate_of` after full text is fetched). We flag rather than delete, since later we may want to study syndication.
- **Why full text is a separate step:** RSS gives headline + short summary. Sentiment on the body is far more reliable than on headlines, but fetching bodies is slower and must be polite, so it runs separately and can be retried.
- **`text_status`:** `pending`, `ok`, `too_short` (paywall/video page), `blocked_robots`, `failed`. Keeping the reason lets us report data-quality numbers in the thesis.
- **robots.txt:** a site's file saying what automated tools may fetch. We check it before every download and skip disallowed pages. This is an ethical and legal safeguard.
- **Metadata vs content:** GDELT gives only URL/title/date. We never treat headline-only rows as full articles.
- **Why SQLite now:** zero setup. The schema is standard SQL, so the move to PostgreSQL later is mechanical.

## Your step-by-step checklist
1. Apply the edits in `CHANGES_TO_EXISTING_FILES.md`; set `USER_AGENT` in `.env` with your own email.
2. Unzip this package **into your repo root** (it adds files, overwrites nothing). Run `pip install -r requirements-dev.txt`.
3. `pytest`: all tests must pass.
4. `python scripts/collect.py init-db`
5. **Verify feeds:** `python scripts/collect.py verify-outlets`. For every OK result set `verified: true` in `config/outlets.yaml`.
6. **Find Hindi feeds** (the important part): for each Hindi outlet run
   `python scripts/collect.py discover-feed https://<homepage>`, add the feed to `outlets.yaml`, then verify again. Target: **4+ English and 4+ Hindi** verified outlets.
7. `python scripts/collect.py rss`, then `python scripts/collect.py stats`.
8. `python scripts/collect.py gdelt`, then check `stats` again.
9. `python scripts/collect.py fulltext --limit 50`. Then check the `text_status` counts in `stats`.
10. Open the database and **read 10 Hindi and 10 English articles yourself** (use DB Browser for SQLite, free). Is the text clean? Any menus or ads left in?
11. Set up automatic running (`docs/scheduling.md`) and leave it for days.
12. Commit using `COMMIT_MESSAGES.md` and push.
