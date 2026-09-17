from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from database import get_db, check_db_connection
from schemas import HealthResponse, StatsResponse
from services.scoring import AnalyticsService
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    """
    try:
        # Check database connection
        db_status = "connected" if check_db_connection() else "disconnected"
        
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
async def get_stats(db: Session = Depends(get_db)):
    """
    Get system statistics
    """
    try:
        stats = AnalyticsService.get_system_statistics(db)
        
        return StatsResponse(**stats)
    
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")