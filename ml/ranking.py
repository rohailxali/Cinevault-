"""
ml/ranking.py — MMR Re-Ranking, Fallback Logic & Recommendation Assembly
=========================================================================
This module is the "brain" of the serving layer. Raw cosine scores are
just a starting point; this module produces the final ranked list that
the API actually serves.

Ranking pipeline:
  1. Start from top-K candidates (precomputed cosine similarities)
  2. Apply MMR (Maximal Marginal Relevance) re-ranking to inject diversity
  3. Apply recency bonus (newer titles get a small boost)
  4. Apply metadata_completeness penalty (minimal titles ranked lower)
  5. Exclude near-zero similarity titles
  6. Determine recommendation_basis label for honest UI copy
  7. Fallback cascade: content_similarity → genre_match → popularity_fallback

MMR (Maximal Marginal Relevance):
  ──────────────────────────────
  Score(i) = λ * sim(i, query) - (1 - λ) * max_j_in_selected sim(i, j)

  λ = 0.7 balances relevance vs diversity. A title that is very similar
  to the query BUT also very similar to an already-selected result is
  penalized. This prevents the top-10 from being "10 slightly different
  versions of the same franchise sequel."

  Why MMR and not clustering?
  Clustering would pre-group all similar titles, but it's a batch
  operation that doesn't adapt to per-query context. MMR is per-query
  and greedy (O(k²) lookups), which is fast for k ≤ 50.

recommendation_basis labels:
  "content_similarity"  — full TF-IDF match
  "genre_match"         — fell back to genre-only overlap
  "popularity_fallback" — no good match; returning popular titles in genre
"""

import json
import numpy as np
from pathlib import Path
from typing import Literal

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
MMR_LAMBDA    = 0.7     # relevance vs diversity trade-off
MIN_SCORE     = 0.05    # exclude titles below this cosine score
RECENCY_BOOST = 0.01    # per-year boost (2021 title gets 0.01 more than 2020)
BASE_YEAR     = 2000    # baseline for recency calculation

RecommendationBasis = Literal["content_similarity", "genre_match", "popularity_fallback"]


def _genre_overlap(genres_a: list[str], genres_b: list[str]) -> float:
    """Jaccard similarity between two genre lists."""
    set_a, set_b = set(genres_a), set(genres_b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _mmr_rerank(
    candidates: list[dict],
    query_sim_scores: dict[str, float],
    all_data_by_id: dict,
    top_n: int,
) -> list[dict]:
    """
    Greedy MMR selection:
      At each step, pick the candidate that maximizes:
        λ * relevance_to_query - (1-λ) * max_similarity_to_selected

    We approximate inter-candidate similarity via genre Jaccard overlap
    (fast, no matrix lookup needed for small k).
    Using cosine scores directly would require an n×n lookup per step,
    which is expensive for k=50 candidates.
    """
    selected  = []
    remaining = list(candidates)

    for _ in range(min(top_n, len(remaining))):
        best_score = -np.inf
        best_item  = None

        for cand in remaining:
            cid          = cand["show_id"]
            relevance    = query_sim_scores.get(cid, 0.0)

            # Diversity penalty: how similar is this to already-selected titles?
            if not selected:
                redundancy = 0.0
            else:
                cand_genres = all_data_by_id.get(cid, {}).get("genres_list", [])
                redundancy  = max(
                    _genre_overlap(
                        cand_genres,
                        all_data_by_id.get(s["show_id"], {}).get("genres_list", [])
                    )
                    for s in selected
                )

            mmr_score = MMR_LAMBDA * relevance - (1 - MMR_LAMBDA) * redundancy
            if mmr_score > best_score:
                best_score = mmr_score
                best_item  = cand

        if best_item:
            selected.append(best_item)
            remaining.remove(best_item)

    return selected


def _recency_bonus(release_year: int) -> float:
    """Small additive bonus for newer titles (max ≈ 0.21 for year 2021)."""
    if not release_year:
        return 0.0
    return max(0.0, (release_year - BASE_YEAR)) * RECENCY_BOOST


def rank_recommendations(
    query_id: str,
    sim_candidates: list[dict],
    all_data_by_id: dict,
    top_n: int = 10,
) -> list[dict]:
    """
    Produce final ranked recommendation list for a given title.

    Args:
        query_id       — show_id of the title we're recommending for
        sim_candidates — list of {"show_id", "score"} from similarity cache
        all_data_by_id — full catalog dict keyed by show_id
        top_n          — number of results to return

    Returns:
        list of recommendation dicts with:
          show_id, score, recommendation_basis, similarity_tier, rank
    """
    query = all_data_by_id.get(query_id, {})
    query_completeness = query.get("metadata_completeness", "full")

    # ── Step 1: Filter near-zero and self ────────────────────────
    candidates = [
        c for c in sim_candidates
        if c["show_id"] != query_id and c["score"] >= MIN_SCORE
    ]

    # ── Step 2: Apply recency bonus ──────────────────────────────
    for c in candidates:
        title_data = all_data_by_id.get(c["show_id"], {})
        c["adjusted_score"] = (
            c["score"] + _recency_bonus(title_data.get("release_year", 0))
        )

    # ── Step 3: Determine recommendation_basis ───────────────────
    if not candidates or query_completeness == "minimal":
        basis: RecommendationBasis = "genre_match"
    elif len(candidates) < 3:
        basis = "genre_match"
    else:
        basis = "content_similarity"

    # ── Step 4: Genre-only fallback (minimal completeness) ───────
    if basis == "genre_match":
        query_genres = set(query.get("genres_list", []))
        if query_genres:
            candidates = [
                c for c in candidates
                if query_genres & set(
                    all_data_by_id.get(c["show_id"], {}).get("genres_list", [])
                )
            ]

    # ── Step 5: Popularity fallback if still empty ───────────────
    if not candidates:
        basis = "popularity_fallback"
        query_genres = set(query.get("genres_list", []))
        candidates = [
            {"show_id": sid, "score": 0.0, "adjusted_score": 0.0}
            for sid, data in all_data_by_id.items()
            if sid != query_id
            and query_genres & set(data.get("genres_list", []))
        ][:top_n * 3]  # take a slice for MMR input

    # ── Step 6: MMR re-ranking ───────────────────────────────────
    query_scores = {c["show_id"]: c.get("adjusted_score", c["score"])
                    for c in candidates}

    ranked = _mmr_rerank(
        candidates     = candidates,
        query_sim_scores = query_scores,
        all_data_by_id = all_data_by_id,
        top_n          = top_n,
    )

    # ── Step 7: Attach metadata & similarity tier label ──────────
    results = []
    for rank_i, item in enumerate(ranked, start=1):
        sid    = item["show_id"]
        score  = item.get("adjusted_score", item.get("score", 0.0))
        tier   = _score_to_tier(score)
        results.append({
            "show_id":              sid,
            "score":                round(score, 4),
            "recommendation_basis": basis,
            "similarity_tier":      tier,
            "rank":                 rank_i,
        })

    return results


def _score_to_tier(score: float) -> str:
    """
    Convert raw cosine score to a human-readable tier label.
    Frontend shows this as a match bar label, NOT the raw decimal.
    This protects against users misinterpreting 0.23 as "23% match."
    """
    if score >= 0.5:  return "Excellent Match"
    if score >= 0.3:  return "Great Match"
    if score >= 0.15: return "Good Match"
    if score >= 0.05: return "Decent Match"
    return "Related"


def build_all_recommendations(
    sim_cache: dict[str, list[dict]],
    all_data_by_id: dict,
    top_n: int = 20,
) -> dict[str, list[dict]]:
    """
    Precompute ranked recommendations for ALL titles and return a
    dict mapping show_id → ranked recommendation list.
    This is called once at pipeline build time; the API serves from this.
    """
    print(f"\n[Ranking] Building recommendations for {len(sim_cache):,} titles…")
    all_recs = {}

    for show_id, candidates in sim_cache.items():
        all_recs[show_id] = rank_recommendations(
            query_id       = show_id,
            sim_candidates = candidates,
            all_data_by_id = all_data_by_id,
            top_n          = top_n,
        )

    print(f"[Ranking] Done. Sample for first title:")
    first_id = next(iter(all_recs))
    for r in all_recs[first_id][:3]:
        print(f"  rank={r['rank']} {r['show_id']} score={r['score']} "
              f"tier='{r['similarity_tier']}' basis='{r['recommendation_basis']}'")

    return all_recs


def save_recommendations(all_recs: dict) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS_DIR / "recommendations.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_recs, f)
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"  [Ranking] Saved recommendations → {path} ({size_mb:.1f} MB)")


def load_recommendations() -> dict:
    path = ARTIFACTS_DIR / "recommendations.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
