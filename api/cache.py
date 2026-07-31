"""
api/cache.py — In-Memory Cache Loader
======================================
Loads ML artifacts into memory at API startup.
The API serves all recommendations from this in-memory cache —
NEVER recomputes on-demand. This is the critical performance decision:
precompute offline, serve from RAM, stay fast at any request rate.

Memory estimate at 8,800 titles:
  clean_data.json       ~  8 MB
  recommendations.json  ~ 15 MB
  Total in-process RAM  ~ 25 MB  — trivial on any modern server

For catalogs > 100K titles, move to:
  - Redis for recommendations (msgpack-serialized)
  - PostgreSQL + pgvector for similarity search
  - The API contract (show_id keyed) stays identical
"""

import json
from pathlib import Path
from typing import Optional

ARTIFACTS_DIR = Path(__file__).parent.parent / "ml" / "artifacts"

_SENTINEL = object()  # unique sentinel for "not yet extracted"


class CineVaultCache:
    """
    Singleton-style cache holding all catalog and recommendation data.
    Loaded once at startup via the FastAPI lifespan event.
    """

    def __init__(self):
        self.titles_by_id:   dict[str, dict] = {}
        self.titles_list:    list[dict]       = []
        self.recommendations: dict[str, list] = {}
        self.genres:         list[str]        = []
        self.loaded:         bool             = False

    def load(self) -> None:
        """Load all artifacts from disk into memory."""
        print("[Cache] Loading CineVault artifacts…")

        # ── Clean catalog ────────────────────────────────────────
        catalog_path = ARTIFACTS_DIR / "clean_data.json"
        if not catalog_path.exists():
            raise FileNotFoundError(
                f"Artifact not found: {catalog_path}\n"
                "Run: python ml/pipeline.py  to build artifacts first."
            )
        with open(catalog_path, "r", encoding="utf-8") as f:
            titles_list = json.load(f, parse_constant=lambda c: None if c == 'NaN' else c)

        self.titles_list  = titles_list
        self.titles_by_id = {t["show_id"]: t for t in titles_list}
        print(f"  [Cache] Catalog loaded: {len(self.titles_list):,} titles")

        # ── Recommendations ───────────────────────────────────────
        recs_path = ARTIFACTS_DIR / "recommendations.json"
        if not recs_path.exists():
            raise FileNotFoundError(f"Artifact not found: {recs_path}")
        with open(recs_path, "r", encoding="utf-8") as f:
            self.recommendations = json.load(f, parse_constant=lambda c: None if c == 'NaN' else c)
        print(f"  [Cache] Recommendations loaded: {len(self.recommendations):,} entries")

        # ── Genre index ──────────────────────────────────────────
        genre_set = set()
        for t in self.titles_list:
            genre_set.update(t.get("genres_list", []))
        self.genres = sorted(genre_set)
        print(f"  [Cache] Genre index: {len(self.genres)} unique genres")

        self.loaded = True
        print("[Cache] Ready to serve.")

    def get_title(self, show_id: str) -> Optional[dict]:
        t = self.titles_by_id.get(show_id)
        if t is None:
            return None

        # Lazy accent color extraction — compute once, stored as sentinel before extraction
        if "accent_color" not in t:
            # Mark as in-progress (prevents repeated hits if color extraction is slow)
            t["accent_color"] = None
            image_url = t.get("backdrop_url") or t.get("poster_url")
            if image_url:
                try:
                    from api.services.color_extractor import extract_accent_color
                    color = extract_accent_color(image_url)
                    t["accent_color"] = color  # None if extraction failed — frontend falls back to gold
                except Exception:
                    t["accent_color"] = None

        return t

    def get_recommendations(self, show_id: str) -> list[dict]:
        return self.recommendations.get(show_id, [])

    def search_titles(self, query: str, limit: int = 20) -> list[dict]:
        """
        Fuzzy title search using RapidFuzz token_set_ratio.
        Returns results sorted by match score descending.
        Threshold: ≥ 45 (permissive enough for partial titles, strict enough
        to avoid garbage results).
        """
        from rapidfuzz import fuzz, process

        q = query.strip().lower()
        if not q:
            return []

        # Build (title, show_id) pairs for rapidfuzz
        choices = {t["show_id"]: t["title"] for t in self.titles_list}
        matches = process.extract(
            query   = q,
            choices = choices,
            scorer  = fuzz.token_set_ratio,
            limit   = limit,
            score_cutoff = 45,
        )
        # matches → [(title, score, show_id), ...]
        results = []
        for title_str, score, show_id in matches:
            t = self.titles_by_id[show_id]
            results.append({**t, "match_score": int(score)})
        return results

    def filter_titles(
        self,
        genre:    Optional[str] = None,
        type_:    Optional[str] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
    ) -> list[dict]:
        """Filter catalog by genre / type / year range."""
        results = self.titles_list
        if genre:
            g_lower = genre.lower()
            results = [
                t for t in results
                if any(g_lower in g.lower() for g in t.get("genres_list", []))
            ]
        if type_:
            results = [t for t in results if t.get("type", "").lower() == type_.lower()]
        if year_min:
            results = [t for t in results if (t.get("release_year") or 0) >= year_min]
        if year_max:
            results = [t for t in results if (t.get("release_year") or 9999) <= year_max]
        return results


# Global singleton — imported by route modules
cache = CineVaultCache()
