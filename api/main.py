"""
api/main.py — CineVault FastAPI Application
============================================
Entrypoint for the API server.

Why FastAPI (not Express/Node)?
  - Python-native: zero serialization overhead between ML artifacts
    (numpy arrays, pandas DataFrames) and the HTTP layer.
  - Async support: handles concurrent requests without blocking.
  - Pydantic integration: automatic request validation + OpenAPI docs.
  - The ML pipeline (sklearn, numpy, pandas) and API share the same
    runtime — no cross-process IPC needed.

Architecture:
  Startup → load ML artifacts into CineVaultCache singleton
  Request → route to handler → serve from cache (no ML computation)
  All recommendations are precomputed; latency is just dict lookup + JSON serialize.

Run with:
  python -m uvicorn api.main:app --reload --port 8000
"""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.cache import cache
from api.models import EventPayload
from api.routes import genres, recommendations, search, titles
from api.routes import ai_search

# ── Interaction event log (future collaborative filtering seed) ────────────
EVENTS_LOG = Path(__file__).parent.parent / "ml" / "artifacts" / "events.jsonl"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan: load cache at startup, flush at shutdown.
    This pattern ensures the cache is always warm before accepting requests.
    """
    # Startup
    cache.load()
    yield
    # Shutdown (nothing to flush — in-memory only)
    print("[API] Shutting down CineVault API.")


# ── App definition ─────────────────────────────────────────────────────────
app = FastAPI(
    title       = "CineVault API",
    description = "Content-based movie & TV show recommendation engine",
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────
# Allow Next.js dev server and production domains (Vercel, etc.)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    os.getenv("FRONTEND_URL", "*"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["GET", "POST"],
    allow_headers     = ["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(titles.router,          prefix="/api/titles",          tags=["Titles"])
app.include_router(recommendations.router, prefix="/api/recommendations",  tags=["Recommendations"])
app.include_router(search.router,          prefix="/api/search",           tags=["Search"])
app.include_router(genres.router,          prefix="/api/genres",           tags=["Genres"])
app.include_router(ai_search.router,       prefix="/api/ai-search",        tags=["AI Search"])


# ── Interaction event stub ─────────────────────────────────────────────────
@app.post("/api/events", tags=["Events"])
async def log_event(payload: EventPayload, request: Request):
    """
    POST /api/events — Log a lightweight interaction event.

    This is a stub for future collaborative filtering signals.
    Events are appended to events.jsonl (one JSON object per line).
    Even if unused now, the log provides the seed data for:
      - Implicit feedback (title_viewed → watch time proxy)
      - Click-through rates (rec_clicked → relevance signal)
      - Future A/B testing

    In production, replace with a proper event streaming system
    (Kafka, Kinesis, or BigQuery streaming insert).
    """
    import datetime
    event = {
        "ts":         datetime.datetime.utcnow().isoformat(),
        "event_type": payload.event_type,
        "show_id":    payload.show_id,
        "query":      payload.query,
        "session_id": payload.session_id,
        "user_agent": request.headers.get("user-agent", ""),
    }
    EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")
    return {"status": "ok"}


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
def health():
    return {
        "status":        "ok",
        "catalog_size":  len(cache.titles_list),
        "genres_count":  len(cache.genres),
        "cache_loaded":  cache.loaded,
    }


# ── Global error handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code = 500,
        content     = {"error": str(exc), "path": str(request.url)},
    )
