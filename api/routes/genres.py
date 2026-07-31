from api.cache import cache
from api.models import GenresResponse
from fastapi import APIRouter

router = APIRouter()


@router.get("", response_model=GenresResponse)
def list_genres():
    """
    GET /api/genres — All unique genres for filter chip UI.
    Sorted alphabetically. Derived from the clean catalog at startup.
    """
    return GenresResponse(genres=cache.genres)
