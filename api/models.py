"""
api/models.py — Pydantic Response Schemas
==========================================
Defines the API contract. All response shapes are typed and validated.
The recommendation_basis and similarity_tier fields are the key "seams"
that allow the frontend to show honest UI copy without hardcoding logic.
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


RecommendationBasis = Literal["content_similarity", "genre_match", "popularity_fallback"]
MetadataCompleteness = Literal["full", "partial", "minimal"]
SimilarityTier = Literal["Excellent Match", "Great Match", "Good Match", "Decent Match", "Related"]


class TitleSummary(BaseModel):
    """Compact title object for list/carousel views."""
    show_id:               str
    type:                  str
    title:                 str
    primary_genre:         str
    genres_list:           list[str]
    release_year:          Optional[int]
    rating:                Optional[str]
    duration:              Optional[str]
    poster_url:            Optional[str]
    metadata_completeness: MetadataCompleteness
    accent_color:          Optional[str] = None   # hex dominant color from backdrop


class TitleDetail(BaseModel):
    """Full title object for detail modal view."""
    show_id:               str
    type:                  str
    title:                 str
    director:              str
    country:               Optional[str]
    country_list:          list[str]
    primary_country:       Optional[str]
    date_added:            Optional[str]
    release_year:          Optional[int]
    rating:                Optional[str]
    rating_tier:           Optional[str]
    duration:              Optional[str]
    duration_value:        Optional[int]
    duration_unit:         Optional[str]
    listed_in:             Optional[str]
    genres_list:           list[str]
    primary_genre:         str
    metadata_completeness: MetadataCompleteness
    poster_url:            Optional[str]
    backdrop_url:          Optional[str]
    tmdb_overview:         Optional[str]
    tmdb_id:               Optional[int]
    accent_color:          Optional[str] = None   # hex dominant color, extracted lazily


class RecommendationItem(BaseModel):
    """A single recommendation entry with ranking metadata."""
    show_id:               str
    rank:                  int
    score:                 float
    recommendation_basis:  RecommendationBasis
    similarity_tier:       SimilarityTier
    title:                 TitleSummary   # embedded for frontend convenience


class RecommendationsResponse(BaseModel):
    """Response from GET /api/recommendations/:id"""
    query_id:              str
    query_title:           str
    count:                 int
    recommendation_basis:  RecommendationBasis   # dominant basis for this result
    recommendations:       list[RecommendationItem]


class TitlesListResponse(BaseModel):
    """Paginated title list response."""
    total:    int
    page:     int
    per_page: int
    pages:    int
    titles:   list[TitleSummary]


class SearchResult(BaseModel):
    """A single fuzzy search result."""
    show_id:    str
    title:      str
    type:       str
    release_year: Optional[int]
    primary_genre: str
    poster_url: Optional[str]
    match_score: int   # RapidFuzz ratio 0–100


class SearchResponse(BaseModel):
    query:   str
    count:   int
    results: list[SearchResult]


class GenresResponse(BaseModel):
    genres: list[str]


class EventPayload(BaseModel):
    """Lightweight interaction event stub for future collaborative filtering."""
    event_type: Literal["title_viewed", "rec_clicked", "search_performed"]
    show_id:    Optional[str] = None
    query:      Optional[str] = None
    session_id: Optional[str] = None


class AISearchRequest(BaseModel):
    """Natural language query from the user for AI-powered intent parsing."""
    query: str = Field(..., min_length=2, max_length=500)


class AISearchIntent(BaseModel):
    """Structured intent extracted from a natural language query by Claude."""
    genres:     list[str] = []
    mood:       list[str] = []
    similar_to: list[str] = []  # title names mentioned by user
    avoid:      list[str] = []  # things user explicitly wants to exclude
    raw_query:  str = ""        # original query for fallback keyword search


class AISearchResponse(BaseModel):
    """Response from POST /api/ai-search."""
    query:      str
    intent:     Optional[AISearchIntent] = None   # None if Claude parsing failed
    results:    list[SearchResult]
    count:      int
    fallback:   bool = False   # True if Claude failed, fell back to keyword match
    fallback_reason: Optional[str] = None
