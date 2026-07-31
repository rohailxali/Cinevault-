"""
ml/audit.py — Dataset Audit & Profiling
========================================
Runs before any model training. Prints a structured report covering:
  - Shape, column types, null counts
  - String-level empty value detection
  - Duplicate title analysis
  - Genre/director cardinality
  - Delimiter consistency check
  - Release year distribution
  - Rating distribution

Design principle: fail loudly if anything unexpected is found so the
downstream pipeline never silently trains on garbage.
"""

import pandas as pd
import re
from collections import Counter


def run_audit(df: pd.DataFrame) -> dict:
    """
    Profile the raw dataset and return an audit report dict.
    Also prints a human-readable summary to stdout.
    """
    print("\n" + "=" * 60)
    print("  CINEVAULT — DATASET AUDIT REPORT")
    print("=" * 60)

    report = {}

    # ── 1. Shape ────────────────────────────────────────────────
    report["shape"] = {"rows": len(df), "cols": len(df.columns)}
    print(f"\n[1] Shape: {len(df):,} rows × {len(df.columns)} columns")
    print(f"    Columns: {df.columns.tolist()}")

    # ── 2. Null counts (including empty-string "null") ───────────
    null_counts = {}
    for col in df.columns:
        true_nulls = int(df[col].isnull().sum())
        empty_str  = int((df[col].astype(str).str.strip() == "").sum())
        null_counts[col] = {"true_nulls": true_nulls, "empty_strings": empty_str}

    report["null_counts"] = null_counts
    print("\n[2] Null / Empty-string counts per column:")
    for col, counts in null_counts.items():
        total = counts["true_nulls"] + counts["empty_strings"]
        flag  = "  ⚠️  MISSING DATA" if total > 0 else ""
        print(f"    {col:<20} true_null={counts['true_nulls']:>4}  "
              f"empty_str={counts['empty_strings']:>4}{flag}")

    # ── 3. Duplicate title detection ─────────────────────────────
    exact_dupes = int(df["title"].duplicated().sum())
    ci_dupes    = int(df["title"].str.lower().str.strip().duplicated().sum())
    report["duplicates"] = {"exact": exact_dupes, "case_insensitive": ci_dupes}
    print(f"\n[3] Duplicate titles:")
    print(f"    Exact duplicates:            {exact_dupes}")
    print(f"    Case-insensitive duplicates: {ci_dupes}")

    # ── 4. Delimiter consistency in listed_in (genres) ───────────
    has_pipe  = int(df["listed_in"].str.contains(r"\|", na=False).sum())
    has_comma = int(df["listed_in"].str.contains(r",",  na=False).sum())
    has_semi  = int(df["listed_in"].str.contains(r";",  na=False).sum())
    report["genre_delimiters"] = {"pipe": has_pipe, "comma": has_comma, "semicolon": has_semi}
    print(f"\n[4] Genre (listed_in) delimiter analysis:")
    print(f"    Pipe-delimited  (|): {has_pipe}")
    print(f"    Comma-delimited (,): {has_comma}")
    print(f"    Semi-delimited  (;): {has_semi}")
    dominant = "comma" if has_comma > max(has_pipe, has_semi) else "pipe"
    print(f"    → Dominant delimiter: {dominant}")

    # ── 5. Genre cardinality ─────────────────────────────────────
    genres = df["listed_in"].str.split(",").explode().str.strip()
    genre_counts = genres.value_counts()
    report["genre_cardinality"] = len(genre_counts)
    report["top_genres"] = genre_counts.head(10).to_dict()
    print(f"\n[5] Genre cardinality: {len(genre_counts)} unique genres")
    print(f"    Top 10 genres:")
    for g, c in genre_counts.head(10).items():
        print(f"      {g:<40} {c:>5}")

    # ── 6. Director cardinality ───────────────────────────────────
    director_counts = df["director"].value_counts()
    report["director_cardinality"] = len(director_counts)
    print(f"\n[6] Director cardinality: {len(director_counts)} unique directors")
    print(f"    Most prolific directors (top 5):")
    for d, c in director_counts.head(5).items():
        print(f"      {d:<35} {c:>3} titles")

    # ── 7. Type distribution ──────────────────────────────────────
    type_dist = df["type"].value_counts().to_dict()
    report["type_distribution"] = type_dist
    print(f"\n[7] Content type distribution:")
    for t, c in type_dist.items():
        print(f"    {t}: {c:,} ({c/len(df)*100:.1f}%)")

    # ── 8. Release year distribution ─────────────────────────────
    year_stats = df["release_year"].describe().to_dict()
    report["year_distribution"] = year_stats
    print(f"\n[8] Release year: min={int(year_stats['min'])} "
          f"max={int(year_stats['max'])} "
          f"median={int(year_stats['50%'])} "
          f"mean={year_stats['mean']:.1f}")

    # ── 9. Rating distribution ────────────────────────────────────
    rating_dist = df["rating"].value_counts().to_dict()
    report["rating_distribution"] = rating_dist
    print(f"\n[9] Rating distribution (top 8):")
    for r, c in list(rating_dist.items())[:8]:
        bar = "█" * (c // 100)
        print(f"    {r:<12} {c:>5}  {bar}")

    # ── 10. Duration format consistency ───────────────────────────
    dur_min     = df["duration"].str.contains("min",    na=False).sum()
    dur_seasons = df["duration"].str.contains("Season", na=False).sum()
    report["duration_formats"] = {"minutes": int(dur_min), "seasons": int(dur_seasons)}
    print(f"\n[10] Duration format:")
    print(f"     'X min'     format: {dur_min}")
    print(f"     'X Season'  format: {dur_seasons}")

    # ── Summary ───────────────────────────────────────────────────
    critical_issues = []
    for col, counts in null_counts.items():
        if counts["true_nulls"] + counts["empty_strings"] > 0:
            critical_issues.append(col)

    if exact_dupes > 0:
        critical_issues.append("duplicate_titles")

    print("\n" + "─" * 60)
    if critical_issues:
        print(f"  ⚠️  Issues found requiring cleaning: {critical_issues}")
    else:
        print("  ✅  No critical issues — dataset is clean. Proceeding to normalization.")
    print("=" * 60 + "\n")

    report["issues"] = critical_issues
    return report


if __name__ == "__main__":
    df = pd.read_csv("../Dataset.csv")
    run_audit(df)
