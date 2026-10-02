# News Intelligence India

A bilingual (Hindi + English) news analysis platform for Indian media. It collects
articles, measures sentiment toward the article and toward individual entities
(people, parties, companies), links Hindi and English coverage of the same event,
and compares how different outlets frame it.

> Status: **Milestone 1 complete (data collection pipeline).** See the roadmap below.

## Research questions
1. Do multilingual transformers fine-tuned on news beat models trained on reviews or tweets?
2. Can we automatically link Hindi and English articles covering the same event?
3. How does tone toward the same entity differ across outlets and languages?

## Architecture (target)
```
RSS / APIs / GDELT -> raw store -> cleaning -> language detection
  -> NER -> entity-level sentiment
  -> article sentiment (+ explanation)
  -> multilingual embeddings -> event clustering
  -> framing comparison
  -> database -> FastAPI -> Next.js dashboard (Vercel)
```

## Repository layout
```
config/          outlets.yaml (news sources)
src/newsintel/   core Python package (config, logging, later: collectors, models)
backend/app/     FastAPI service
frontend/        Next.js dashboard (deployed on Vercel)
data/            raw, processed, annotations (kept out of git)
notebooks/       experiments (Colab/Kaggle friendly)
scripts/         helper scripts
tests/           automated tests
docs/            notes and report material
```

## Quick start
```bash
# 1. Python environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .

# 2. Config
cp .env.example .env             # Windows: copy .env.example .env

# 3. Verify
python scripts/check_env.py
pytest

# 4. Run backend (terminal 1)
uvicorn backend.app.main:app --reload --port 8000
#    open http://localhost:8000/health

# 5. Run frontend (terminal 2)
cd frontend
cp .env.example .env.local
npm install
npm run dev
#    open http://localhost:3000

# 6. Initialise and run the data collection pipeline (Milestone 1)
python scripts/collect.py init-db    # create the database
python scripts/collect.py verify-outlets
python scripts/collect.py rss
```

## Roadmap
| Milestone | Topic | Status |
|---|---|---|
| 0 | Project setup | done |
| 1 | Data collection pipeline | done |
| 2 | Preprocessing and annotation | next |
| 3 | Sentiment models | |
| 4 | NER and entity-level sentiment | |
| 5 | Cross-lingual event linking | |
| 6 | Framing analysis | |
| 7 | Backend API | |
| 8 | Frontend dashboard | |
| 9 | Deployment and report | |

## Data and licensing
Raw article text may be copyrighted. The repository does not store raw articles;
only code, configuration, and (later) our own annotations and article URLs/IDs.
