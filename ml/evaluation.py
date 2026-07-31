"""
ml/evaluation.py — Recommendation Quality Metrics
===================================================
Implements:
  - Precision@K   — what fraction of top-K recs are "relevant"?
  - Recall@K      — what fraction of all relevant titles are retrieved?
  - MAP@K         — Mean Average Precision, penalizes bad rank ordering
  - Human-readable qualitative check harness

Proxy relevance definition:
  Since we have no real user interaction data (this is cold-start
  content-based filtering), we define relevance via a proxy:
  A title B is "relevant" to title A if:
    - They share ≥ 1 genre AND
    - They share the same type (Movie/TV Show)

  This is a floor-level relevance definition — it will overcount
  relevant items (many titles share a genre) but gives us a consistent
  signal for comparing ranking strategies.

  Limitation (documented):
  ─────────────────────────
  This evaluation has NO real user feedback loop. A title that shares
  a genre but is tonally opposite (e.g., two "Dramas" — one is a
  light rom-com, one is a war film) will both count as "relevant" here.
  True validation requires:
    - A/B testing with real watch-through rates
    - Implicit feedback (clicks, completion rate, re-visits)
    - Explicit ratings
  This evaluation is best used to catch regressions (e.g., new feature
  engineering that scores WORSE on the proxy) rather than to claim
  absolute recommendation quality.
"""

import numpy as np
from collections import defaultdict


def _is_relevant(query: dict, candidate: dict) -> bool:
    """
    Proxy relevance: same type + at least 1 overlapping genre.
    Conservative: we don't require director match (too strict for cold-start).
    """
    if query.get("type") != candidate.get("type"):
        return False
    q_genres = set(query.get("genres_list", []))
    c_genres = set(candidate.get("genres_list", []))
    return bool(q_genres & c_genres)


def precision_at_k(
    recommendations: list[dict],
    query: dict,
    all_data_by_id: dict,
    k: int = 10,
) -> float:
    """
    Fraction of top-K recommendations that are relevant to the query.
    P@K = |{relevant titles in top K}| / K
    """
    top_k = recommendations[:k]
    if not top_k:
        return 0.0
    relevant = sum(
        1 for r in top_k
        if _is_relevant(query, all_data_by_id.get(r["show_id"], {}))
    )
    return relevant / len(top_k)


def recall_at_k(
    recommendations: list[dict],
    query: dict,
    all_data_by_id: dict,
    k: int = 10,
) -> float:
    """
    Fraction of all relevant titles (in the catalog) that appear in top-K.
    R@K = |{relevant titles in top K}| / |all relevant titles in catalog|
    Note: "all relevant titles" can be large (many same-genre titles),
    so R@K will naturally be low — this is expected for content-based systems.
    """
    top_k   = recommendations[:k]
    all_rel = [
        sid for sid, data in all_data_by_id.items()
        if sid != query.get("show_id") and _is_relevant(query, data)
    ]
    if not all_rel:
        return 0.0
    in_top_k = sum(
        1 for r in top_k
        if _is_relevant(query, all_data_by_id.get(r["show_id"], {}))
    )
    return in_top_k / len(all_rel)


def average_precision_at_k(
    recommendations: list[dict],
    query: dict,
    all_data_by_id: dict,
    k: int = 10,
) -> float:
    """
    Average Precision@K — penalizes systems that rank relevant items lower.
    AP@K = (1/|relevant|) * Σ P@i * rel(i)  for i in 1..k
    where rel(i) = 1 if i-th result is relevant, 0 otherwise.
    """
    top_k   = recommendations[:k]
    all_rel = sum(
        1 for sid, data in all_data_by_id.items()
        if sid != query.get("show_id") and _is_relevant(query, data)
    )
    if all_rel == 0:
        return 0.0

    running_precision = 0.0
    relevant_found    = 0

    for i, r in enumerate(top_k, start=1):
        if _is_relevant(query, all_data_by_id.get(r["show_id"], {})):
            relevant_found    += 1
            running_precision += relevant_found / i

    return running_precision / min(all_rel, k)


def compute_metrics(
    all_recs: dict[str, list[dict]],
    all_data_by_id: dict,
    sample_size: int = 200,
    k: int = 10,
) -> dict:
    """
    Compute Precision@K, Recall@K, MAP@K over a random sample of titles.
    Using a sample (default 200) to keep runtime reasonable; at 8800 titles
    this still gives statistically meaningful estimates.
    """
    print(f"\n[Evaluation] Computing metrics over {sample_size} sampled titles "
          f"(k={k})…")

    np.random.seed(42)
    sampled_ids = np.random.choice(
        list(all_recs.keys()),
        size=min(sample_size, len(all_recs)),
        replace=False,
    )

    p_scores, r_scores, ap_scores = [], [], []

    for sid in sampled_ids:
        query = all_data_by_id.get(sid, {})
        recs  = all_recs.get(sid, [])

        p_scores.append(precision_at_k(recs, query, all_data_by_id, k))
        r_scores.append(recall_at_k(recs, query, all_data_by_id, k))
        ap_scores.append(average_precision_at_k(recs, query, all_data_by_id, k))

    metrics = {
        f"Precision@{k}": round(float(np.mean(p_scores)), 4),
        f"Recall@{k}":    round(float(np.mean(r_scores)), 4),
        f"MAP@{k}":       round(float(np.mean(ap_scores)), 4),
    }

    print(f"\n  ┌─ EVALUATION RESULTS (proxy-relevance, n={sample_size}) ─────┐")
    for metric, val in metrics.items():
        bar = "█" * int(val * 40)
        print(f"  │  {metric:<15} {val:.4f}  {bar}")
    print(f"  └────────────────────────────────────────────────────────────┘")
    print(f"\n  ⚠️  Limitation: Proxy relevance (genre+type overlap) may overcount")
    print(f"     relevant items. No real user feedback loop yet. These metrics")
    print(f"     are best used for regression testing, not absolute quality claims.")

    return metrics


def qualitative_check(
    query_id: str,
    all_recs: dict,
    all_data_by_id: dict,
    top_n: int = 10,
) -> None:
    """
    Human-readable sanity check: print top-N recs with genre/director
    overlap highlighted. Use this to spot-check recommendation quality.
    """
    query    = all_data_by_id.get(query_id, {})
    recs     = all_recs.get(query_id, [])[:top_n]
    q_genres = set(query.get("genres_list", []))
    q_dir    = query.get("director", "")

    print(f"\n{'─'*70}")
    print(f"  QUALITATIVE CHECK: '{query.get('title')}' ({query.get('release_year')})")
    print(f"  Type: {query.get('type')} | Genres: {', '.join(q_genres)}")
    print(f"  Director: {q_dir}")
    print(f"{'─'*70}")

    for r in recs:
        rec      = all_data_by_id.get(r["show_id"], {})
        r_genres = set(rec.get("genres_list", []))
        shared   = q_genres & r_genres
        dir_match = "✓ dir" if rec.get("director") == q_dir and q_dir else ""

        print(f"  #{r['rank']:<2} {rec.get('title', '?'):<40} "
              f"[{r['similarity_tier']}]  "
              f"shared={','.join(shared) if shared else 'none'} {dir_match}")
    print(f"  Basis: {recs[0]['recommendation_basis'] if recs else 'N/A'}")
    print(f"{'─'*70}")
