# Edits to files that already exist in your repo

The zip only ADDS new files. Make these small edits by hand (or let Antigravity do it).
Do not overwrite the whole files, because your versions contain fixes from Milestone 0.

## 1. `requirements.txt`: append
```
requests>=2.31
feedparser>=6.0
trafilatura>=1.8
```

## 2. `.env.example` (and your real `.env`): append
```
# --- Collection ---
# Identify your bot politely: include a contact email so site owners can reach you.
USER_AGENT=BhashaPulseBot/0.1 (student research project; contact: your-email@example.com)
# Seconds to wait between requests to the same website.
REQUEST_DELAY_SECONDS=2
```

## 3. `scripts/check_env.py`
In the tuple of packages checked, add `"requests"`, `"feedparser"`, `"trafilatura"`.
(Find the line `for pkg in ("yaml", "dotenv", "fastapi", "uvicorn"):`.)

## 4. `README.md`: roadmap table
Change Milestone 0 to `done`, Milestone 1 to `done` after you finish, and Milestone 2 to `next`.
Also add this line under "Quick start":
```
python scripts/collect.py init-db    # create the database (Milestone 1)
```

## 5. `config/outlets.yaml`
The zip includes a ready `config/outlets.yaml` (8 outlets: 4 English, 4 Hindi, all
`verified: false`). Replace your file with it. Then run `verify-outlets` and set
`verified: true` only for the OK ones; fix any FAIL feed URL yourself.
