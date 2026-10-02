"""Backend API (FastAPI).

Milestone 0 only has a health check so we can prove the frontend can talk to
the backend. Real endpoints (articles, sentiment trends, entities...) arrive in
Milestone 7.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from newsintel import __version__
from newsintel.config import get_settings

settings = get_settings()

app = FastAPI(title="News Intelligence India API", version=__version__)

# CORS: lets the browser-based frontend (a different origin) call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "outlets_configured": len(settings.outlets),
    }
