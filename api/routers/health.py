"""
api/routers/health.py — GET /health endpoint.
No auth required. Used as keep-alive ping target.
Returns environment and index status.
"""

from fastapi import APIRouter
from api.config import get_settings
from api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check. No auth required.
    Keep-alive ping target — prevents cold starts on free tier.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        index_document_count=0,  # TODO: query AI Search for live count
    )
