"""
ml/similarity.py — Cosine Similarity Computation & Caching
============================================================
Precomputes pairwise cosine similarity for all titles and caches
the top-K results per title as a JSON structure for fast API serving.

Algorithm choice — linear_kernel vs cosine_similarity:
  ─────────────────────────────────────────────────────
  We use sklearn.metrics.pairwise.linear_kernel (dot product) rather
  than cosine_similarity. For L2-normalized TF-IDF vectors (which
  TfidfVectorizer produces by default), these are mathematically
  identical: cos(a,b) = dot(a,b) / (|a| * |b|) = dot(a,b) when
  |a| = |b| = 1.

  linear_kernel is faster because it skips the norm computation step,
  operating directly on the sparse matrix without densification.
  cosine_similarity would call linear_kernel internally anyway after
  normalizing, so using it directly avoids the double-norm overhead.

  ⚠️  IMPORTANT: We do NOT compute the full n×n dense similarity matrix
  (8800×8800 = 77M floats ≈ 310MB dense). Instead we compute one row
  at a time (or in batches) and keep only the top-K per title.

Scale note:
  For catalogs > 10K titles, replace this with an ANN (Approximate
  Nearest Neighbor) index:
    - FAISS IndexFlatIP: exact inner-product search, GPU-accelerated
    - Annoy / ScaNN: tree-based ANN for memory-constrained serving
  The API contract (return top-N by show_id) stays identical.
"""

import json
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import linear_kernel

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
TOP_K = 50   # precompute top-50; API will re-rank and return top-10 or top-20


def compute_topk_similarity(
    tfidf_matrix,
    show_ids: list[str],
    top_k: int = TOP_K,
    batch_size: int = 500,
) -> dict[str, list[dict]]:
    """
    Compute top-K most similar titles for every title.

    Uses batched row-wise linear_kernel to avoid materializing the
    full n×n matrix in memory. Each batch produces a (batch_size × n)
    dense submatrix, from which we extract top-K and discard the rest.

    Args:
        tfidf_matrix : sparse (n_titles × n_features) TF-IDF matrix
        show_ids     : list of show_id strings (same order as matrix rows)
        top_k        : number of similar titles to keep per title
        batch_size   : number of titles to process per batch

    Returns:
        dict mapping show_id → list of {"show_id": str, "score": float}
        sorted descending by score (self excluded, score > 0.01 only).
    """
    print(f"\n[Similarity] Computing top-{top_k} similarities "
          f"for {len(show_ids):,} titles (batch_size={batch_size})…")

    n = tfidf_matrix.shape[0]
    results: dict[str, list[dict]] = {}
    id_to_idx = {sid: i for i, sid in enumerate(show_ids)}

    for start in range(0, n, batch_size):
        end     = min(start + batch_size, n)
        batch   = tfidf_matrix[start:end]           # sparse slice
        scores  = linear_kernel(batch, tfidf_matrix)  # (batch × n) dense

        for local_i, global_i in enumerate(range(start, end)):
            row_scores = scores[local_i]             # 1-D array length n
            sid = show_ids[global_i]

            # Exclude self (score = 1.0 for self)
            row_scores[global_i] = -1.0

            # Get top-K indices, exclude near-zero scores
            top_indices = np.argsort(row_scores)[::-1][:top_k]
            neighbors = [
                {"show_id": show_ids[idx], "score": float(row_scores[idx])}
                for idx in top_indices
                if row_scores[idx] > 0.01   # exclude irrelevant titles
            ]
            results[sid] = neighbors

        pct = (end / n) * 100
        if end % (batch_size * 5) == 0 or end == n:
            print(f"  [Similarity] {end:>5}/{n} ({pct:.0f}%)")

    print(f"[Similarity] Done. {len(results):,} titles processed.")
    return results


def save_similarity_cache(sim_cache: dict) -> None:
    """Save top-K cache to JSON for API consumption."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACTS_DIR / "similarity_cache.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sim_cache, f)
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"  [Similarity] Saved cache → {out_path} ({size_mb:.1f} MB)")


def load_similarity_cache() -> dict:
    """Load the precomputed similarity cache."""
    path = ARTIFACTS_DIR / "similarity_cache.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
