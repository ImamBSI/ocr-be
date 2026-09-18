from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.cv import CandidateResponse


class ScoringRequest(BaseModel):
    """Request untuk scoring"""

    job_requirement_id: str


class BatchScoringRequest(BaseModel):
    """Request untuk batch scoring"""

    candidate_ids: List[str] = Field(..., min_length=1)
    job_requirement_id: str


class ScoringResponse(BaseModel):
    """Response untuk scoring result"""

    id: str
    candidate_id: str
    score: float
    rank: Optional[int] = None
    matched_criteria: Dict[str, float]
    status: str = "success"
    message: Optional[str] = None
    created_at: datetime


class BatchScoringResponse(BaseModel):
    """Response untuk batch scoring"""

    total: int
    scored: int
    failed: int
    results: List[ScoringResponse]


class RankedCandidateResponse(CandidateResponse):
    """Response untuk ranked candidate"""

    score: float
    ranking: int
    matched_criteria: Dict[str, float]