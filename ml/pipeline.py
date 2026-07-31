# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
ml/pipeline.py -- CineVault ML Pipeline Orchestrator
====================================================
Single entrypoint to build all ML artifacts from scratch.
Run this before starting the API server.

Pipeline stages:
  1. Load raw CSV
  2. Audit (report + validation)
  3. Clean & normalize
  4. Fetch TMDB posters / overview (async, cached)
  5. Feature engineering (weighted content profiles)
  6. TF-IDF vectorization
  7. Cosine similarity computation (batched, top-50)
  8. MMR re-ranking → build recommendation cache
  9. Evaluation (Precision@K, MAP@K + qualitative checks)
  10. Save clean_data.json (served by API)

Usage:
  python ml/pipeline.py

Output artifacts (ml/artifacts/):
  clean_data.json        — full catalog with all enriched fields
  tfidf_matrix.npz       — sparse TF-IDF matrix (for debugging)
  vectorizer.pkl         — fitted TfidfVectorizer
  similarity_cache.json  — raw top-50 per title
  recommendations.json   — final ranked top-20 per title
  poster_cache.json      — TMDB fetch cache (resumable)
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.audit       import run_audit
from ml.cleaner     import clean
from ml.fetch_posters import fetch_posters
from ml.features    import engineer_features
from ml.vectorizer  import fit_vectorizer, save_artifacts
from ml.similarity  import compute_topk_similarity, save_similarity_cache
from ml.ranking     import build_all_recommendations, save_recommendations
from ml.evaluation  import compute_metrics, qualitative_check

DATASET_PATH  = Path(__file__).parent.parent / "Dataset.csv"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

# Qualitative check titles — these are well-known Netflix titles to sanity-check
QUALITATIVE_TITLES = [
    "Inception",           # should recommend: Interstellar, Tenet, The Dark Knight
    "Breaking Bad",        # should recommend: Ozark, Narcos, Better Call Saul
    "The Crown",           # should recommend: historical dramas
    "Bird Box",            # should recommend: thrillers / horror
    "Stranger Things",     # should recommend: sci-fi / kids shows
]


def _df_to_catalog(df: pd.DataFrame) -> dict:
    """
    Convert cleaned DataFrame to a dict keyed by show_id for O(1) lookup.
    Serializes list columns (genres_list, country_list) correctly.
    """
    catalog = {}
    for _, row in df.iterrows():
        sid = row["show_id"]
        catalog[sid] = {
            "show_id":               sid,
            "type":                  row["type"],
            "title":                 row["title"],
            "director":              row["director"],
            "country":               row["country"],
            "country_list":          row["country_list"] if isinstance(row["country_list"], list) else [],
            "primary_country":       row["primary_country"],
            "date_added":            str(row["date_added"]) if pd.notna(row["date_added"]) else None,
            "release_year":          int(row["release_year"]) if pd.notna(row["release_year"]) else None,
            "rating":                row["rating"],
            "rating_tier":           row.get("rating_tier", ""),
            "duration":              row["duration"],
            "duration_value":        int(row["duration_value"]) if pd.notna(row.get("duration_value")) else None,
            "duration_unit":         row.get("duration_unit"),
            "listed_in":             row["listed_in"],
            "genres_list":           row["genres_list"] if isinstance(row["genres_list"], list) else [],
            "primary_genre":         row["primary_genre"],
            "metadata_completeness": row["metadata_completeness"],
            "poster_url":            row.get("poster_url"),
            "backdrop_url":          row.get("backdrop_url"),
            "tmdb_overview":         row.get("tmdb_overview"),
            "tmdb_id":               row.get("tmdb_id"),
            "content_profile":       row.get("content_profile", ""),
        }
    return catalog


def run_pipeline(skip_posters: bool = False) -> None:
    """
    Execute the full CineVault ML pipeline.

    Args:
        skip_posters: If True, skip TMDB fetch (useful for quick iteration).
                      Posters will be None and frontend uses gradient fallback.
    """
    t_start = time.time()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  CINEVAULT -- ML PIPELINE STARTING")
    print("=" * 64)

    # ── Stage 1: Load ────────────────────────────────────────────
    print(f"\n[Stage 1/9] Loading dataset from {DATASET_PATH}…")
    df = pd.read_csv(DATASET_PATH)
    print(f"  Loaded {len(df):,} rows × {len(df.columns)} columns")

    # ── Stage 2: Audit ───────────────────────────────────────────
    print("\n[Stage 2/9] Running dataset audit…")
    audit_report = run_audit(df)
    with open(ARTIFACTS_DIR / "audit_report.json", "w") as f:
        json.dump(audit_report, f, indent=2, default=str)

    # ── Stage 3: Clean ───────────────────────────────────────────
    print("\n[Stage 3/9] Cleaning & normalizing…")
    df_clean = clean(df)

    # ── Stage 4: TMDB Poster Fetch ───────────────────────────────
    if not skip_posters:
        print("\n[Stage 4/9] Fetching TMDB posters & overviews…")
        df_clean = fetch_posters(df_clean)
    else:
        print("\n[Stage 4/9] Skipping TMDB fetch (skip_posters=True)")

    # ── Stage 5: Feature Engineering ────────────────────────────
    # Important: run AFTER poster fetch so tmdb_overview enriches profiles
    print("\n[Stage 5/9] Engineering content profiles…")
    df_feat = engineer_features(df_clean)

    # ── Stage 6: Vectorization ───────────────────────────────────
    print("\n[Stage 6/9] TF-IDF vectorization…")
    profiles      = df_feat["content_profile"].tolist()
    show_ids      = df_feat["show_id"].tolist()
    vectorizer, tfidf_matrix = fit_vectorizer(profiles)
    save_artifacts(vectorizer, tfidf_matrix)

    # ── Stage 7: Similarity ──────────────────────────────────────
    print("\n[Stage 7/9] Computing cosine similarities (batched)…")
    sim_cache = compute_topk_similarity(tfidf_matrix, show_ids, top_k=50)
    save_similarity_cache(sim_cache)

    # ── Stage 8: Ranking ─────────────────────────────────────────
    print("\n[Stage 8/9] MMR re-ranking → building recommendation cache…")
    catalog   = _df_to_catalog(df_feat)
    all_recs  = build_all_recommendations(sim_cache, catalog, top_n=20)
    save_recommendations(all_recs)

    # ── Stage 9: Save clean catalog ──────────────────────────────
    print("\n[Stage 9/9] Saving clean catalog JSON…")
    catalog_path = ARTIFACTS_DIR / "clean_data.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(list(catalog.values()), f, ensure_ascii=False, default=str)
    size_mb = catalog_path.stat().st_size / 1024 / 1024
    print(f"  Saved {len(catalog):,} titles → {catalog_path} ({size_mb:.1f} MB)")

    # ── Evaluation ───────────────────────────────────────────────
    print("\n[Evaluation] Running metrics…")
    metrics = compute_metrics(all_recs, catalog, sample_size=300, k=10)
    with open(ARTIFACTS_DIR / "eval_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Qualitative checks for 5 well-known titles
    print("\n[Evaluation] Qualitative checks:")
    title_to_id = {v["title"].lower(): k for k, v in catalog.items()}
    for qt in QUALITATIVE_TITLES:
        qid = title_to_id.get(qt.lower())
        if qid:
            qualitative_check(qid, all_recs, catalog, top_n=10)
        else:
            print(f"  [skip] '{qt}' not found in catalog")

    # ── Summary ──────────────────────────────────────────────────
    elapsed = time.time() - t_start
    print(f"\n" + "=" * 64)
    print(f"  PIPELINE COMPLETE in {elapsed:.0f}s")
    print(f"  Artifacts in: ml/artifacts/")
    print(f"  Metrics: {metrics}")
    print("=" * 64)
    print(f"\n  Next step: python -m uvicorn api.main:app --reload --port 8000")


if __name__ == "__main__":
    # Pass --skip-posters for quick dev iteration without TMDB calls
    skip = "--skip-posters" in sys.argv
    run_pipeline(skip_posters=skip)
