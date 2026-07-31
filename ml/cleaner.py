"""
ml/cleaner.py — Data Cleaning & Normalization
==============================================
Responsibilities:
  1. Normalize genre (listed_in) delimiter → consistent Python list
  2. Standardize casing / strip whitespace on all string fields
  3. Deduplicate titles (exact + case-insensitive)
  4. Parse duration into numeric minutes (movies) or season count (TV)
  5. Assign metadata_completeness flag: full / partial / minimal
     — Used downstream by the ranking layer to choose fallback strategy
     — Defined even though this dataset has no true nulls, because
       "Unknown" director or single-genre entries are semantically sparse.

Why tag completeness instead of dropping sparse rows?
  Dropping rows with weak metadata would silently shrink the catalog
  and surprise users who search for those titles. Instead we surface
  them with honest UI copy ("Popular in this genre") while still
  keeping them browsable.
"""

import re
import pandas as pd
from rapidfuzz import fuzz


# ── Constants ────────────────────────────────────────────────────────────────
UNKNOWN_DIRECTORS = {"", "unknown", "n/a", "na", "not available", "none"}
TMDB_IMAGE_BASE   = "https://image.tmdb.org/t/p/w500"


def _normalize_genres(raw: str) -> list[str]:
    """
    Split genres by comma (the only delimiter in this dataset).
    Strip whitespace and normalize casing to Title Case.
    e.g. "action & adventure ,Dramas" → ["Action & Adventure", "Dramas"]
    """
    if pd.isna(raw) or str(raw).strip() == "":
        return []
    # Handle comma, pipe, or semicolon just in case future data has them
    parts = re.split(r"[,|;]", str(raw))
    return [p.strip().title() for p in parts if p.strip()]


def _parse_duration(raw: str, content_type: str) -> dict:
    """
    Parse the mixed 'duration' field into structured form:
      Movies  → {"value": 90, "unit": "min"}
      TV Show → {"value": 3, "unit": "seasons"}
    Returns {"value": None, "unit": None} if unparseable.
    """
    if pd.isna(raw):
        return {"value": None, "unit": None}
    raw = str(raw).strip()
    if content_type == "Movie":
        m = re.search(r"(\d+)\s*min", raw, re.IGNORECASE)
        if m:
            return {"value": int(m.group(1)), "unit": "min"}
    else:
        m = re.search(r"(\d+)\s*season", raw, re.IGNORECASE)
        if m:
            return {"value": int(m.group(1)), "unit": "seasons"}
    return {"value": None, "unit": None}


def _assign_completeness(row: pd.Series) -> str:
    """
    Tag each title with a metadata_completeness level.

    Tiers:
      full    — has director + ≥2 genres + country + year + rating
      partial — missing director OR has only 1 genre
      minimal — no usable director (unknown/blank) AND only 1 genre

    The ranking module uses this to choose recommendation strategy:
      full    → content_similarity  (TF-IDF cosine)
      partial → content_similarity  (with lower confidence)
      minimal → genre_match fallback → popularity_fallback

    This tiering ensures we never silently serve low-quality recommendations
    without labeling them as such in the API response.
    """
    director_ok = (
        pd.notna(row["director"])
        and str(row["director"]).strip().lower() not in UNKNOWN_DIRECTORS
    )
    genres     = row.get("genres_list", [])
    genre_rich = len(genres) >= 2
    country_ok = pd.notna(row["country"]) and str(row["country"]).strip() != ""

    if director_ok and genre_rich and country_ok:
        return "full"
    elif director_ok or genre_rich:
        return "partial"
    else:
        return "minimal"


def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate titles using a two-pass strategy:
      Pass 1 — Exact case-insensitive + year match (fast)
      Pass 2 — Fuzzy title match (RapidFuzz token_sort_ratio ≥ 92)
               within the same release_year — catches OCR/typo variants.

    We keep the first occurrence (stable sort preserves dataset order).
    Dropped rows are logged so nothing is silently lost.
    """
    original_len = len(df)

    # Pass 1: case-insensitive exact dedup
    df["_title_key"] = df["title"].str.lower().str.strip() + "|" + df["release_year"].astype(str)
    before = len(df)
    df = df.drop_duplicates(subset=["_title_key"], keep="first")
    print(f"  [dedup pass-1] Removed {before - len(df)} exact duplicates")

    # Pass 2: fuzzy dedup within same year
    # Only applied if the dataset is small enough (< 20K) to avoid O(n²) pain.
    # At 8,790 rows this is fast enough (~seconds).
    records  = df.to_dict("records")
    keep_ids = set()
    dropped  = 0

    for i, rec_a in enumerate(records):
        if rec_a["show_id"] in keep_ids:
            continue  # already flagged for removal
        for j in range(i + 1, len(records)):
            rec_b = records[j]
            if rec_b["show_id"] in keep_ids:
                continue
            # Only compare within same year to bound the search space
            if rec_a["release_year"] != rec_b["release_year"]:
                continue
            score = fuzz.token_sort_ratio(
                rec_a["title"].lower(), rec_b["title"].lower()
            )
            if score >= 92:
                keep_ids.add(rec_b["show_id"])
                dropped += 1

    if dropped:
        df = df[~df["show_id"].isin(keep_ids)]
    print(f"  [dedup pass-2] Removed {dropped} fuzzy near-duplicates (score ≥ 92)")

    df = df.drop(columns=["_title_key"])
    print(f"  [dedup] {original_len:,} → {len(df):,} rows after deduplication")
    return df.reset_index(drop=True)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main cleaning entrypoint. Returns a fully normalized DataFrame
    with additional derived columns ready for feature engineering.
    """
    print("\n[Cleaner] Starting normalization…")
    df = df.copy()

    # ── 1. Strip whitespace from all string columns ───────────────
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip())

    # ── 2. Normalize title casing (preserve intentional caps like "CODA") ──
    # We don't lower-case titles — that destroys UX display.
    # But we strip and remove non-printable characters.
    df["title"] = df["title"].str.strip()

    # ── 3. Director → clean string (keep as-is, already single name) ─
    df["director"] = df["director"].fillna("Unknown").str.strip()

    # ── 4. Country → list (some titles have "United States, France") ─
    df["country_list"] = df["country"].apply(
        lambda x: [c.strip().title() for c in str(x).split(",") if c.strip()]
        if pd.notna(x) else []
    )
    # Primary country (first listed)
    df["primary_country"] = df["country_list"].apply(
        lambda lst: lst[0] if lst else "Unknown"
    )

    # ── 5. Genre normalization ────────────────────────────────────
    df["genres_list"] = df["listed_in"].apply(_normalize_genres)
    # First genre = primary (used for fallback grouping)
    df["primary_genre"] = df["genres_list"].apply(
        lambda g: g[0] if g else "Unknown"
    )

    # ── 6. Duration parsing ───────────────────────────────────────
    df["duration_parsed"] = df.apply(
        lambda r: _parse_duration(r["duration"], r["type"]), axis=1
    )
    df["duration_value"] = df["duration_parsed"].apply(lambda d: d["value"])
    df["duration_unit"]  = df["duration_parsed"].apply(lambda d: d["unit"])

    # ── 7. Rating normalization ───────────────────────────────────
    df["rating"] = df["rating"].fillna("NR").str.strip().str.upper()

    # ── 8. Date parsing ───────────────────────────────────────────
    df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")
    df["year_added"] = df["date_added"].dt.year.fillna(0).astype(int)

    # ── 9. Deduplication ─────────────────────────────────────────
    df = _deduplicate(df)

    # ── 10. Metadata completeness tag ────────────────────────────
    df["metadata_completeness"] = df.apply(_assign_completeness, axis=1)
    dist = df["metadata_completeness"].value_counts().to_dict()
    print(f"  [completeness] Distribution: {dist}")

    # ── 11. Placeholder for TMDB poster URL (filled in fetch_posters.py) ──
    df["poster_url"]   = None
    df["backdrop_url"] = None
    df["tmdb_overview"] = None   # TMDB synopsis — enriches our sparse dataset!
    df["tmdb_id"]      = None

    print(f"[Cleaner] Done. Output shape: {df.shape}")
    return df
