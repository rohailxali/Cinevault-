from api.cache import cache
from api.models import TitlesListResponse, TitleDetail, TitleSummary
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import math

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


def _to_detail(t: dict) -> TitleDetail:
    return TitleDetail(
        show_id=t["show_id"],
        type=t.get("type", ""),
        title=t.get("title", ""),
        director=t.get("director", "Unknown"),
        country=t.get("country"),
        country_list=t.get("country_list", []),
        primary_country=t.get("primary_country"),
        date_added=t.get("date_added"),
        release_year=t.get("release_year"),
        rating=t.get("rating"),
        rating_tier=t.get("rating_tier"),
        duration=t.get("duration"),
        duration_value=t.get("duration_value"),
        duration_unit=t.get("duration_unit"),
        listed_in=t.get("listed_in"),
        genres_list=t.get("genres_list", []),
        primary_genre=t.get("primary_genre", ""),
        metadata_completeness=t.get("metadata_completeness", "full"),
        poster_url=t.get("poster_url"),
        backdrop_url=t.get("backdrop_url"),
        tmdb_overview=t.get("tmdb_overview"),
        tmdb_id=t.get("tmdb_id"),
    )


@router.get("", response_model=TitlesListResponse)
def list_titles(
    page:     int           = Query(1, ge=1),
    per_page: int           = Query(24, ge=1, le=100),
    genre:    Optional[str] = Query(None, description="Filter by genre substring"),
    type:     Optional[str] = Query(None, description="Movie or TV Show"),
    year_min: Optional[int] = Query(None),
    year_max: Optional[int] = Query(None),
):
    """
    GET /api/titles — Paginated catalog listing with optional filters.
    Returns TitleSummary objects (no heavy fields like content_profile).
    """
    filtered = cache.filter_titles(
        genre=genre, type_=type, year_min=year_min, year_max=year_max
    )
    total    = len(filtered)
    pages    = max(1, math.ceil(total / per_page))
    start    = (page - 1) * per_page
    end      = start + per_page
    page_items = filtered[start:end]

    return TitlesListResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        titles=[_to_summary(t) for t in page_items],
    )


@router.get("/featured", response_model=list[TitleSummary])
def get_featured(limit: int = Query(10, ge=1, le=30)):
    """
    GET /api/titles/featured — Returns high-quality titles for hero/featured
    sections. Selects titles that have: backdrop image + full metadata.
    Falls back to top titles by recency if fewer than `limit` have backdrops.
    """
    # Prefer titles with backdrop images (for hero section)
    with_backdrop = [
        t for t in cache.titles_list
        if t.get("backdrop_url") and t.get("metadata_completeness") == "full"
    ]
    # Sort by recency
    with_backdrop.sort(key=lambda t: t.get("release_year", 0), reverse=True)

    if len(with_backdrop) >= limit:
        return [_to_summary(t) for t in with_backdrop[:limit]]

    # Fallback: take any recent full-metadata title
    fallback = [
        t for t in cache.titles_list
        if t.get("metadata_completeness") == "full"
    ]
    fallback.sort(key=lambda t: t.get("release_year", 0), reverse=True)
    return [_to_summary(t) for t in fallback[:limit]]


@router.get("/{show_id}", response_model=TitleDetail)
def get_title(show_id: str):
    """GET /api/titles/:id — Full title detail."""
    title = cache.get_title(show_id)
    if not title:
        raise HTTPException(status_code=404, detail=f"Title '{show_id}' not found")
    return _to_detail(title)
