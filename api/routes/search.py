from api.cache import cache
from api.models import SearchResponse, SearchResult
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("", response_model=SearchResponse)
def search(
    q:     str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(12, ge=1, le=50),
):
    """
    GET /api/search?q= — Fuzzy title search.
    Uses RapidFuzz token_set_ratio for permissive partial matching.
    Threshold: 45 (catches "Dark Knig" → "The Dark Knight").
    Returns results sorted by match score descending.
    """
    results = cache.search_titles(q.strip(), limit=limit)
    return SearchResponse(
        query=q,
        count=len(results),
        results=[
            SearchResult(
                show_id=r["show_id"],
                title=r["title"],
                type=r.get("type", ""),
                release_year=r.get("release_year"),
                primary_genre=r.get("primary_genre", ""),
                poster_url=r.get("poster_url"),
                match_score=r.get("match_score", 0),
            )
            for r in results
        ],
    )
