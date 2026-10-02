# Running collection automatically

Articles only accumulate if the collector runs repeatedly. RSS feeds show just the
latest 20-50 items, so run every 3-6 hours.

## Why not GitHub Actions yet?
A GitHub Actions job starts on a clean machine every time, so a SQLite file would
be lost after each run. Until we move to a hosted Postgres database (Milestone 9),
run the collector on your own computer.

## Option A: Windows (Task Scheduler)
1. Open Task Scheduler -> Create Basic Task -> name it "BhashaPulse collect".
2. Trigger: Daily, then in Properties repeat every 6 hours for 1 day.
3. Action: Start a program
   - Program: `C:\path\to\Bhasha-Pulse\.venv\Scripts\python.exe`
   - Arguments: `scripts\collect.py run-all`
   - Start in: `C:\path\to\Bhasha-Pulse`
4. Tick "Run task as soon as possible after a scheduled start is missed".

## Option B: Linux / macOS (cron)
```
crontab -e
0 */6 * * * cd /path/to/Bhasha-Pulse && .venv/bin/python scripts/collect.py run-all >> data/collect.log 2>&1
```

## Option C: simple and manual
Run `python scripts/collect.py run-all` whenever you sit down to work. Fine for the
first week; automate once the pipeline is proven.

## Laptop sleeps?
Collection pauses while it sleeps. That is fine: the next run just picks up newer items.
If you need 24/7 collection, a free-tier cloud VM is an option later.

## Back up the database
`data/newsintel.sqlite` is your dataset. Copy it to Google Drive weekly. It is not in git.
