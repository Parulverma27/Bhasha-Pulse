# Milestone 0: Project Setup (read this first)

## What this milestone does
It creates the **foundation** of the project: folder structure, configuration,
environment, a minimal backend, a minimal frontend, tests, and CI. No ML yet.
Everything in later milestones plugs into this structure.

## What is inside `news-intel-india/`
| Path | Purpose | Why it exists |
|---|---|---|
| `src/newsintel/config.py` | Loads settings from `.env` and `config/outlets.yaml` | One place for configuration, so no secrets or paths are scattered through the code |
| `src/newsintel/logging_setup.py` | Standard log format | Every script logs the same way, which makes debugging easier |
| `config/outlets.yaml` | List of news outlets (id, language, RSS URL) | Milestone 1 reads this to know where to collect from |
| `backend/app/main.py` | FastAPI app with `/health` | Proves the backend runs and the frontend can reach it |
| `frontend/` | Minimal Next.js page that calls `/health` | Proves the Vercel-ready frontend works; the real dashboard is Milestone 8 |
| `scripts/check_env.py` | Checks Python, Git, Node, packages, `.env` | Quick "is my machine ready?" test |
| `tests/test_config.py` | Unit tests for config loading | Catches bad outlet files early |
| `.github/workflows/ci.yml` | Runs lint and tests on every push | Shows professional engineering practice |
| `.gitignore`, `.env.example` | Keep secrets, data and models out of git | Protects API keys and avoids committing copyrighted articles |
| `data/` | raw / processed / annotations folders | Data stays local and is not pushed to GitHub |

## Key concepts to understand (for your viva)
- **`.env` vs `.env.example`:** `.env` holds your real keys and is never committed; `.env.example` is a template that is committed.
- **`pip install -e .`:** installs `newsintel` in editable mode so `from newsintel.config import ...` works anywhere in the project.
- **CORS:** the frontend (port 3000 / Vercel) and backend (port 8000) are different origins; the backend must explicitly allow the frontend.
- **`NEXT_PUBLIC_` prefix:** Next.js only exposes env variables to the browser if they start with this prefix. Never put secrets there.
- **CI:** GitHub automatically runs tests when you push, so broken code is caught.

## Your step-by-step checklist (do these yourself)
1. Create an empty GitHub repo named `news-intel-india` (no README, no .gitignore).
2. Install: Python 3.10+, Git, Node.js LTS, VS Code.
3. Unzip this package and open the `news-intel-india` folder in VS Code (or Antigravity).
4. Follow the "Quick start" in `news-intel-india/README.md`.
5. Run `python scripts/check_env.py` until everything shows PASS.
6. Run `pytest`. All tests should pass.
7. Open `http://localhost:8000/health` and `http://localhost:3000`. The page should say "Backend is up".
8. Open each outlet RSS URL in a browser. Set `verified: true` for those that work, and add more outlets (3-4 more English, 4 more Hindi). Fix or replace any broken feed.
9. Make your first commits using `COMMIT_MESSAGES.md` and push to GitHub.

## Definition of done
- [ ] `check_env.py` shows all PASS
- [ ] `pytest` passes
- [ ] Backend `/health` returns status ok
- [ ] Frontend page shows "Backend is up"
- [ ] `outlets.yaml` has at least 8 outlets (4 English, 4 Hindi), each verified by you
- [ ] Code pushed to GitHub, and the CI badge/run is green

## Viva questions for this milestone
1. Why did we separate `src/newsintel`, `backend`, and `frontend`?
2. Why is `data/` in `.gitignore`?
3. What problem does CORS solve, and where is it configured?
4. Why do we keep the ML pipeline separate from the web API?
5. Why will ML analysis run in batch and store results in a database, instead of running models on Vercel?
6. What is the purpose of CI in this project?

## Known limitations at this milestone
- RSS URLs in `outlets.yaml` are **unverified starting points**; sites change feeds, so check them.
- The frontend is a placeholder. Design and charts come in Milestone 8.
- Dependencies are not pinned to exact versions yet; we will freeze them before final deployment.

## Next: Milestone 1 (Data collection pipeline)
RSS + GDELT + news API collectors, full-text extraction, deduplication, database schema, and a scheduled job.
