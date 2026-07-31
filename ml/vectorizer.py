"""
ml/vectorizer.py — TF-IDF Vectorization
=========================================
Converts content profiles into sparse TF-IDF feature vectors.

Algorithm choice — Why TF-IDF (not embeddings)?
  ─────────────────────────────────────────────
  ✅ Our feature space is dominated by categorical labels (genre names,
     director names, country names, rating tiers) that are already
     semantically unambiguous. "Action & Adventure" doesn't need a
     neural embedding to understand it means action + adventure.

  ✅ TF-IDF handles the key challenge: common words like "international"
     or "drama" appear in many titles (high DF → low IDF weight),
     while niche tokens like "stop_motion" or a specific director name
     correctly get higher weight — exactly the signal we want.

  ✅ Dataset size: ~8,800 titles. The full TF-IDF matrix fits in RAM
     (<100MB sparse). No GPU, no ONNX runtime, no model download.

  ✅ Interpretable: we can explain "recommended because both are 
     Action & Adventure directed by the same person" from token weights.

  When to upgrade to sentence embeddings (e.g., all-MiniLM-L6-v2):
  ─────────────────────────────────────────────────────────────────
  ⬆ When the dataset has rich description/synopsis fields (natural
    language, not just category labels) AND the catalog is > 50K titles.
  ⬆ When you need semantic similarity across paraphrased concepts
    (e.g., "heist movie" ≈ "bank robbery thriller") that TF-IDF misses.
  ⬆ When you're willing to pay the latency/compute cost of encoding.

Hyperparameter choices:
  ngram_range=(1, 2)  — Captures bigrams like "action adventure",
                        "science fiction", "stand up" which are
                        meaningful compound genre tokens.
  sublinear_tf=True   — log(1 + tf) dampens the effect of our
                        intentional token repetition (weighting trick)
                        so it doesn't completely dominate IDF.
                        The repetition still biases scores, but doesn't
                        swamp the signal from rarer tokens.
  min_df=2            — Ignore tokens appearing in only 1 title
                        (likely noise / typos).
  max_df=0.85         — Ignore tokens in >85% of titles (too common
                        to discriminate — e.g., "movie", "film").
  stop_words='english'— Removes standard English stopwords.
"""

import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import save_npz, load_npz


ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def fit_vectorizer(profiles: list[str]) -> tuple:
    """
    Fit a TF-IDF vectorizer on content profiles and return
    (vectorizer, tfidf_matrix).

    Returns:
        vectorizer  — fitted TfidfVectorizer (serialize for reuse)
        tfidf_matrix — sparse matrix (n_titles × n_features)
    """
    print("\n[Vectorizer] Fitting TF-IDF…")

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        sublinear_tf=True,        # log(1+tf) — see module docstring
        stop_words="english",
        min_df=2,                 # cut hapax legomena (single-title tokens)
        max_df=0.85,              # cut near-universal tokens
        analyzer="word",
        strip_accents="unicode",  # normalizes é→e, ñ→n etc.
        token_pattern=r"(?u)\b[\w&]+\b",  # keep & for "Action & Adventure"
    )

    tfidf_matrix = vectorizer.fit_transform(profiles)

    n_titles, n_features = tfidf_matrix.shape
    print(f"  [Vectorizer] Matrix: {n_titles:,} titles × {n_features:,} features")
    print(f"  [Vectorizer] Sparsity: "
          f"{(1 - tfidf_matrix.nnz / (n_titles * n_features)) * 100:.1f}%")

    return vectorizer, tfidf_matrix


def save_artifacts(vectorizer, tfidf_matrix) -> None:
    """Persist vectorizer and matrix to disk for API loading."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(ARTIFACTS_DIR / "vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)

    save_npz(str(ARTIFACTS_DIR / "tfidf_matrix.npz"), tfidf_matrix)
    print(f"  [Vectorizer] Saved artifacts to {ARTIFACTS_DIR}")


def load_artifacts():
    """Load previously fitted vectorizer and matrix."""
    with open(ARTIFACTS_DIR / "vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    tfidf_matrix = load_npz(str(ARTIFACTS_DIR / "tfidf_matrix.npz"))
    return vectorizer, tfidf_matrix
