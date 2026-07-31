"""
ml/fetch_posters.py — TMDB Poster & Metadata Fetching
======================================================
Enriches the cleaned dataset with:
  - poster_url    (TMDB w500 poster image)
  - backdrop_url  (TMDB w1280 backdrop for hero section)
  - tmdb_overview (synopsis — our dataset has no description field!)
  - tmdb_id       (TMDB identifier for deep linking)

Authentication: Bearer token (API Read Access Token v4)
  — Token lives in .env as TMDB_BEARER_TOKEN
  — Sent as Authorization: Bearer <token> header
  — Never appears in URLs or query strings

Rate limiting: TMDB allows ~50 req/sec.
  We use asyncio + httpx with a semaphore (20 concurrent) and
  exponential backoff on 429 responses.

Strategy:
  1. Search TMDB by title + year using /search/movie or /search/tv
  2. Take the first result (highest popularity match)
  3. Fall back to title-only search if year-match finds nothing
  4. If still no match: poster_url stays None → frontend gradient fallback

Cache: Results stored to ml/artifacts/poster_cache.json.
  Re-running the pipeline skips already-fetched titles.
  This means the poster fetch is idempotent and resumable.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
import pandas as pd
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ARTIFACTS_DIR    = Path(__file__).parent / "artifacts"
CACHE_FILE       = ARTIFACTS_DIR / "poster_cache.json"
TMDB_BASE        = "https://api.themoviedb.org/3"
TMDB_IMG_BASE    = "https://image.tmdb.org/t/p"
BEARER_TOKEN     = os.getenv("TMDB_BEARER_TOKEN", "")
MAX_CONCURRENT   = 20
REQUEST_TIMEOUT  = 8.0   # seconds
MAX_RETRIES      = 3


def _make_headers() -> dict:
    if not BEARER_TOKEN:
        raise ValueError("TMDB_BEARER_TOKEN not set in .env")
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "accept":        "application/json",
    }


def _build_urls(poster_path: str | None, backdrop_path: str | None) -> tuple:
    poster   = f"{TMDB_IMG_BASE}/w500{poster_path}"   if poster_path   else None
    backdrop = f"{TMDB_IMG_BASE}/w1280{backdrop_path}" if backdrop_path else None
    return poster, backdrop


async def _search_tmdb(
    client: httpx.AsyncClient,
    title: str,
    year: int,
    content_type: str,   # "Movie" or "TV Show"
    semaphore: asyncio.Semaphore,
) -> dict | None:
    """
    Search TMDB for a single title. Returns dict with poster/backdrop/overview,
    or None if not found.
    """
    endpoint = "/search/movie" if content_type == "Movie" else "/search/tv"
    params   = {"query": title, "include_adult": False}
    if year and year > 1900:
        params["year" if content_type == "Movie" else "first_air_date_year"] = year

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.get(
                    f"{TMDB_BASE}{endpoint}",
                    params=params,
                    headers=_make_headers(),
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code == 429:
                    # Rate limited — exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code != 200:
                    return None

                data    = resp.json()
                results = data.get("results", [])

                if not results:
                    # Retry without year constraint
                    if "year" in params or "first_air_date_year" in params:
                        params.pop("year", None)
                        params.pop("first_air_date_year", None)
                        continue
                    return None

                best = results[0]
                poster, backdrop = _build_urls(
                    best.get("poster_path"),
                    best.get("backdrop_path"),
                )
                overview = best.get("overview", "") or ""
                return {
                    "tmdb_id":      best.get("id"),
                    "poster_url":   poster,
                    "backdrop_url": backdrop,
                    "tmdb_overview": overview[:500] if overview else None,
                }

            except (httpx.TimeoutException, httpx.RequestError):
                await asyncio.sleep(1)

    return None


async def _fetch_all(
    titles: list[dict],
    existing_cache: dict,
) -> dict:
    """
    Async batch fetch for all titles. Skips already-cached show_ids.
    """
    to_fetch = [t for t in titles if t["show_id"] not in existing_cache]
    print(f"  [TMDB] {len(existing_cache)} cached / {len(to_fetch)} to fetch…")

    if not to_fetch:
        return existing_cache

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    cache     = dict(existing_cache)

    async with httpx.AsyncClient(http2=False) as client:
        tasks = [
            _search_tmdb(
                client       = client,
                title        = t["title"],
                year         = t.get("release_year", 0),
                content_type = t.get("type", "Movie"),
                semaphore    = semaphore,
            )
            for t in to_fetch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    found = 0
    for t, result in zip(to_fetch, results):
        if isinstance(result, dict):
            cache[t["show_id"]] = result
            found += 1
        else:
            cache[t["show_id"]] = {
                "tmdb_id":      None,
                "poster_url":   None,
                "backdrop_url": None,
                "tmdb_overview": None,
            }

    print(f"  [TMDB] Found posters for {found}/{len(to_fetch)} titles "
          f"({found/len(to_fetch)*100:.1f}%)")
    return cache


def fetch_posters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main entrypoint. Fetches TMDB data for all titles in df,
    merges results back, saves cache. Returns enriched DataFrame.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing cache (idempotent / resumable)
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            existing_cache = json.load(f)
        print(f"  [TMDB] Loaded {len(existing_cache)} cached entries")
    else:
        existing_cache = {}

    titles = df[["show_id", "title", "release_year", "type"]].to_dict("records")

    # Run async fetch
    print(f"\n[TMDB] Fetching poster/backdrop/overview for {len(titles):,} titles…")
    cache = asyncio.run(_fetch_all(titles, existing_cache))

    # Save updated cache
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)
    print(f"  [TMDB] Cache saved → {CACHE_FILE}")

    # Merge into DataFrame
    df = df.copy()
    df["poster_url"]    = df["show_id"].map(lambda s: cache.get(s, {}).get("poster_url"))
    df["backdrop_url"]  = df["show_id"].map(lambda s: cache.get(s, {}).get("backdrop_url"))
    df["tmdb_overview"] = df["show_id"].map(lambda s: cache.get(s, {}).get("tmdb_overview"))
    df["tmdb_id"]       = df["show_id"].map(lambda s: cache.get(s, {}).get("tmdb_id"))

    poster_found = df["poster_url"].notna().sum()
    print(f"  [TMDB] Posters resolved: {poster_found:,}/{len(df):,} "
          f"({poster_found/len(df)*100:.1f}%)")

    return df
