"""
api/routes/ai_search.py — AI Conversational Search Endpoint
=============================================================
POST /api/ai-search

Accepts a free-text natural language query, uses Claude to extract
structured intent (genres, mood, similar titles, things to avoid),
then maps that intent into the existing TF-IDF/cosine-similarity pipeline.

Security: ANTHROPIC_API_KEY is read from server-side env only. Never
exposed to the client. This route is FastAPI (Python) only.

Failure modes:
  - Claude API down / timeout → fallback to keyword search
  - Malformed / non-JSON Claude response → fallback to keyword search
  - Missing API key → fallback to keyword search, log warning once
  - All fallbacks set `fallback=True` in the response so the UI can show
    a subtle "showing closest keyword matches" note.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

from fastapi import APIRouter
from rapidfuzz import fuzz

from api.cache import cache
from api.models import (
    AISearchRequest,
    AISearchResponse,
    AISearchIntent,
    SearchResult,
)

router = APIRouter()

# ── Claude client (lazy init so missing key doesn't crash startup) ──────────
_anthropic_client = None
_key_warning_issued = False


def _get_client():
    global _anthropic_client, _key_warning_issued
    if _anthropic_client is not None:
        return _anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        if not _key_warning_issued:
            print("[AI Search] WARNING: ANTHROPIC_API_KEY not set. AI search will fall back to keyword search.")
            _key_warning_issued = True
        return None
    try:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
        return _anthropic_client
    except Exception as e:
        print(f"[AI Search] Failed to init Anthropic client: {e}")
        return None


# ── Intent extraction ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a film and TV recommendation assistant. 
Extract structured intent from the user's natural language query.
Return ONLY valid JSON with this exact schema — no markdown, no explanation:
{
  "genres": ["list of genre strings matching Netflix/streaming genres"],
  "mood": ["list of mood/tone descriptors like: dark, funny, heartwarming, intense, slow-burn, action-packed"],
  "similar_to": ["list of exact movie or TV show titles mentioned by the user"],
  "avoid": ["list of things user explicitly wants to exclude"]
}
Rules:
- genres must match common streaming genres: Action & Adventure, Comedy, Drama, Horror, Romance, Sci-Fi & Fantasy, Thriller, Documentary, Animation, Crime, etc.
- If the query is vague, infer sensible defaults.
- If nothing matches a field, use an empty array [].
- Never return null values."""


def _extract_intent(query: str) -> Optional[AISearchIntent]:
    """Call Claude to parse the user's query into structured intent. Returns None on any failure."""
    client = _get_client()
    if client is None:
        return None

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=256,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": query}],
            timeout=8.0,
        )
        raw = message.content[0].text.strip()

        # Strip any accidental markdown fences
        raw = re.sub(r"^```json\s*|```$", "", raw.strip(), flags=re.MULTILINE).strip()

        data = json.loads(raw)
        return AISearchIntent(
            genres=data.get("genres", []),
            mood=data.get("mood", []),
            similar_to=data.get("similar_to", []),
            avoid=data.get("avoid", []),
            raw_query=query,
        )
    except Exception as e:
        print(f"[AI Search] Claude parsing failed: {e}")
        return None


# ── Intent → results mapping ─────────────────────────────────────────────────

def _score_title(t: dict, intent: AISearchIntent) -> float:
    """
    Score a catalog title against extracted intent.
    Returns a composite score (higher = better match).
    """
    score = 0.0
    title_genres = {g.lower() for g in t.get("genres_list", [])}
    overview = (t.get("tmdb_overview", "") or "").lower()
    title_text = (t.get("title", "") or "").lower()

    # Genre overlap (most important signal)
    for g in intent.genres:
        if g.lower() in title_genres:
            score += 3.0
        elif any(g.lower() in tg for tg in title_genres):
            score += 1.5

    # Mood/tone keyword match against overview
    for m in intent.mood:
        if m.lower() in overview:
            score += 1.5

    # Similar-to: find the mentioned title in our catalog, get its genre signal
    for ref_title in intent.similar_to:
        ref_score = fuzz.token_set_ratio(ref_title.lower(), title_text)
        if ref_score > 70:
            score += 2.0  # exact or near title match

    # Penalty: avoid keywords in title or overview
    for avoid_kw in intent.avoid:
        avoid_lower = avoid_kw.lower()
        if avoid_lower in overview or any(avoid_lower in g for g in title_genres):
            score -= 5.0

    return score


def _intent_to_results(intent: AISearchIntent, limit: int = 20) -> list[dict]:
    """Map structured intent to catalog titles using our existing cache."""
    # If user mentioned specific titles, seed from their recommendations first
    seeded: list[dict] = []
    for ref_title in intent.similar_to:
        matches = cache.search_titles(ref_title, limit=3)
        for m in matches:
            recs = cache.get_recommendations(m["show_id"])
            for r in recs[:5]:
                rec_t = cache.get_title(r["show_id"])
                if rec_t and rec_t not in seeded:
                    seeded.append(rec_t)

    # Score and rank the full catalog (or seeded subset if large enough)
    candidates = seeded if len(seeded) >= 30 else cache.titles_list
    scored = [(t, _score_title(t, intent)) for t in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [t for t, s in scored[:limit] if s > 0]


def _dict_to_search_result(t: dict, score: int = 80) -> SearchResult:
    return SearchResult(
        show_id=t["show_id"],
        title=t.get("title", ""),
        type=t.get("type", ""),
        release_year=t.get("release_year"),
        primary_genre=t.get("primary_genre", ""),
        poster_url=t.get("poster_url"),
        match_score=score,
    )


# ── Route ────────────────────────────────────────────────────────────────────

@router.post("", response_model=AISearchResponse)
async def ai_search(body: AISearchRequest):
    """
    POST /api/ai-search — Natural language movie/show search.

    1. Call Claude to parse intent from free-text query.
    2. Map intent into catalog using genre + mood + similar-to scoring.
    3. Fallback to keyword search if Claude fails.
    """
    query = body.query.strip()

    intent = _extract_intent(query)

    if intent is not None:
        # Happy path: AI-powered results
        raw_results = _intent_to_results(intent, limit=20)

        if raw_results:
            results = [_dict_to_search_result(t, 85) for t in raw_results]
            return AISearchResponse(
                query=query,
                intent=intent,
                results=results,
                count=len(results),
                fallback=False,
            )

    # Fallback: keyword search (Claude failed or returned no results)
    keyword_results = cache.search_titles(query, limit=20)
    results = [_dict_to_search_result(t, t.get("match_score", 60)) for t in keyword_results]

    return AISearchResponse(
        query=query,
        intent=intent,
        results=results,
        count=len(results),
        fallback=True,
        fallback_reason="AI parsing failed or returned no results — showing closest keyword matches",
    )
