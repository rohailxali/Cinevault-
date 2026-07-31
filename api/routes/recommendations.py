from api.cache import cache
from api.models import RecommendationsResponse, RecommendationItem, TitleSummary
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def _to_summary(t: dict) -> TitleSummary:
    return TitleSummary(
        show_id=t["show_id"],
        type=t.get("type", ""),
        title=t.get("title", ""),
        primary_genre=t.get("primary_genre", ""),
        genres_list=t.get("genres_list", []),
        release_year=t.get("release_year"),
        rating=t.get("rating"),
        duration=t.get("duration"),
        poster_url=t.get("poster_url"),
        metadata_completeness=t.get("metadata_completeness", "full"),
    )


@router.get("/{show_id}", response_model=RecommendationsResponse)
def get_recommendations(
    show_id: str,
    n: int = Query(10, ge=1, le=20, description="Number of recommendations"),
):
    """
    GET /api/recommendations/:id — Ranked recommendations for a title.

    Returns a list of RecommendationItem objects, each containing:
      - The recommended title (TitleSummary)
      - recommendation_basis: what drove this recommendation
        "content_similarity" | "genre_match" | "popularity_fallback"
      - similarity_tier: human-readable match label (not raw score)
        "Excellent Match" | "Great Match" | "Good Match" | "Decent Match" | "Related"
      - rank: 1-based position in the re-ranked list

    This API contract creates the seam between ML and UI:
    the frontend uses recommendation_basis to show honest copy
    ("Similar to this title" vs "Popular in this genre")
    WITHOUT any business logic in the frontend code.
    """
    query_title = cache.get_title(show_id)
    if not query_title:
        raise HTTPException(status_code=404, detail=f"Title '{show_id}' not found")

    raw_recs = cache.get_recommendations(show_id)
    if not raw_recs:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for '{show_id}'. "
                   "Rebuild the ML pipeline if this is unexpected."
        )

    # Slice to requested N
    raw_recs = raw_recs[:n]

    # Enrich with title data
    items = []
    for rec in raw_recs:
        rec_title_data = cache.get_title(rec["show_id"])
        if not rec_title_data:
            continue   # Title was deduped out — skip cleanly
        items.append(
            RecommendationItem(
                show_id=rec["show_id"],
                rank=rec["rank"],
                score=rec["score"],
                recommendation_basis=rec["recommendation_basis"],
                similarity_tier=rec["similarity_tier"],
                title=_to_summary(rec_title_data),
            )
        )

    # Determine dominant basis for the response-level field
    # (usually all items have the same basis, but in edge cases they differ)
    basis_counts: dict[str, int] = {}
    for item in items:
        basis_counts[item.recommendation_basis] = (
            basis_counts.get(item.recommendation_basis, 0) + 1
        )
    dominant_basis = max(basis_counts, key=basis_counts.get) if basis_counts else "content_similarity"

    return RecommendationsResponse(
        query_id=show_id,
        query_title=query_title.get("title", ""),
        count=len(items),
        recommendation_basis=dominant_basis,
        recommendations=items,
    )
