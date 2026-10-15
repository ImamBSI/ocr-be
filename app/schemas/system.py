from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    database: str


class StatsResponse(BaseModel):
    total_candidates: int
    total_jobs: int
    total_uploads: int
    total_scores: int
    average_score: Optional[float] = None
    highest_score: Optional[float] = None
    lowest_score: Optional[float] = None