"""
ml/features.py — Feature Engineering & Content Profile Builder
==============================================================
Builds a single weighted text "content profile" per title that the
TF-IDF vectorizer will consume.

Weighting scheme (justified below):
  ┌─────────────────┬────────┬─────────────────────────────────────────┐
  │ Field           │ Weight │ Rationale                               │
  ├─────────────────┼────────┼─────────────────────────────────────────┤
  │ genres          │  3×    │ Primary signal — genre is what users    │
  │                 │        │ consciously sort by ("I want a comedy") │
  ├─────────────────┼────────┼─────────────────────────────────────────┤
  │ director        │  2×    │ "More from this director" is a real     │
  │                 │        │ discovery pattern (auteur-driven)       │
  ├─────────────────┼────────┼─────────────────────────────────────────┤
  │ type            │  2×    │ Movie vs TV Show — users rarely browse  │
  │                 │        │ across type boundaries accidentally     │
  ├─────────────────┼────────┼─────────────────────────────────────────┤
  │ tmdb_overview   │  2×    │ Rich description from TMDB fetch —      │
  │                 │        │ weighted same as director since we      │
  │                 │        │ can't verify quality of all synopses   │
  ├─────────────────┼────────┼─────────────────────────────────────────┤
  │ primary_country │  1×    │ Weak signal but helps cluster           │
  │                 │        │ International content meaningfully      │
  ├─────────────────┼────────┼─────────────────────────────────────────┤
  │ rating          │  1×    │ Content rating proximity matters        │
  │                 │        │ (TV-MA ≈ R, TV-Y ≈ G)                  │
  ├─────────────────┼────────┼─────────────────────────────────────────┤
  │ title words     │  1×    │ Low weight — title overlap is mostly    │
  │                 │        │ franchise detection, not semantic match │
  └─────────────────┴────────┴─────────────────────────────────────────┘

We also keep genres and director as structured fields (list) separately
so the ranking module can apply exact-match boosting if needed.

Upgrade path: if the dataset becomes description-rich (all titles have
a synopsis), swap the TF-IDF approach for sentence-transformers
(e.g., all-MiniLM-L6-v2) which understands semantic similarity in
natural language rather than token co-occurrence.
"""

import re
import pandas as pd


# Rating similarity groups — titles with same tier are more compatible
RATING_TIERS = {
    "TV-MA": "mature", "R": "mature", "NC-17": "mature",
    "TV-14": "teen",   "PG-13": "teen",
    "TV-PG": "family", "PG": "family",
    "TV-G":  "kids",   "G": "kids",
    "TV-Y7": "kids",   "TV-Y": "kids", "TV-Y7-FV": "kids",
    "NR": "unrated",   "UR": "unrated",
}


def _clean_text(text: str) -> str:
    """Remove special characters, normalize whitespace."""
    if not text or pd.isna(text):
        return ""
    text = str(text)
    text = re.sub(r"[^\w\s&]", " ", text)   # keep & (for "Action & Adventure")
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def _repeat(tokens: list[str], times: int) -> str:
    """Repeat a list of tokens N times to boost TF weight."""
    joined = " ".join(tokens)
    return " ".join([joined] * times)


def build_content_profile(row: pd.Series) -> str:
    """
    Assemble the weighted content profile text blob for a single title.
    The profile is the document that TF-IDF will vectorize.

    Repetition is the weighting mechanism: repeating 'Action Drama' 3×
    means TF-IDF assigns those tokens 3× the term frequency of a 1×
    token, biasing cosine similarity toward genre-matching titles.
    This is a well-understood trick in content-based filtering and more
    interpretable than custom kernel weights.
    """
    parts = []

    # ── Genres (3×) ──────────────────────────────────────────────
    genres = row.get("genres_list", [])
    if genres:
        genre_tokens = [_clean_text(g) for g in genres]
        parts.append(_repeat(genre_tokens, 3))

    # ── Director (2×) ────────────────────────────────────────────
    director = str(row.get("director", "")).strip()
    if director and director.lower() not in ("unknown", "n/a", ""):
        dir_token = _clean_text(director).replace(" ", "_")  # treat as single token
        parts.append(_repeat([dir_token], 2))

    # ── Type (2×) ────────────────────────────────────────────────
    content_type = str(row.get("type", "")).strip().lower().replace(" ", "_")
    if content_type:
        parts.append(_repeat([content_type], 2))

    # ── TMDB overview (2×) if available ──────────────────────────
    overview = row.get("tmdb_overview", "")
    if overview and str(overview).strip() and str(overview).strip().lower() != "none":
        parts.append(_repeat([_clean_text(str(overview))], 2))

    # ── Primary country (1×) ─────────────────────────────────────
    country = str(row.get("primary_country", "")).strip()
    if country and country.lower() not in ("unknown", ""):
        parts.append(_clean_text(country).replace(" ", "_"))

    # ── Rating tier (1×) ─────────────────────────────────────────
    rating = str(row.get("rating", "")).strip().upper()
    tier   = RATING_TIERS.get(rating, "")
    if tier:
        parts.append(tier)

    # ── Title words (1×, stopwords already handled by TF-IDF) ────
    title_words = _clean_text(str(row.get("title", "")))
    if title_words:
        parts.append(title_words)

    return " ".join(parts)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add content_profile column and rating_tier to the cleaned DataFrame.
    These are the primary inputs to the vectorization step.
    """
    print("\n[Features] Building content profiles…")
    df = df.copy()

    df["content_profile"] = df.apply(build_content_profile, axis=1)
    df["rating_tier"]     = df["rating"].map(RATING_TIERS).fillna("unrated")

    # Sanity check: flag profiles that are suspiciously short
    short_profiles = (df["content_profile"].str.split().str.len() < 5).sum()
    if short_profiles > 0:
        print(f"  ⚠️  {short_profiles} titles have very short content profiles "
              f"(< 5 tokens) — will fall back to genre_match or popularity_fallback")

    avg_len = df["content_profile"].str.split().str.len().mean()
    print(f"  [Features] Average profile length: {avg_len:.1f} tokens")
    print(f"[Features] Done.")
    return df
