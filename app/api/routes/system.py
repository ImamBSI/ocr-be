import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repos
from app.db.base import Repositories
from app.db.factory import check_storage
from app.schemas.system import HealthResponse, StatsResponse
from app.services.scoring import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check(repos: Repositories = Depends(get_repos)):
    """Health check endpoint."""
    try:
        db_status = "connected" if check_storage() else "disconnected"

        return HealthResponse(
            status="ok" if db_status == "connected" else "degraded",
            version="1.0.0",
            database=db_status,
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="error",
            version="1.0.0",
            database="error",
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(repos: Repositories = Depends(get_repos)):
    """Get system statistics."""
    try:
        stats = AnalyticsService.get_system_statistics(repos)
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")