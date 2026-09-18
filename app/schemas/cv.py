from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProcessCVResponse(BaseModel):
    """Response untuk CV processing"""

    id: str
    name: str
    email: str
    phone: Optional[str] = None
    experience_years: int
    skills: List[str]
    education: Optional[str] = None
    cv_text: str
    status: str = "success"
    message: Optional[str] = None


class CandidateRequest(BaseModel):
    """Request untuk create/update candidate"""

    name: str = Field(..., min_length=1, max_length=255)
    email: str
    phone: Optional[str] = None
    experience_years: int = Field(default=0, ge=0)
    skills: List[str] = Field(default=[])
    education: Optional[str] = None
    cv_text: Optional[str] = None


class CandidateResponse(CandidateRequest):
    """Response untuk single candidate"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    is_processed: bool
    created_at: datetime
    updated_at: datetime


class CandidateDetailResponse(CandidateResponse):
    """Response detail candidate dengan score info"""

    score: Optional[float] = None
    ranking: Optional[int] = None
    matched_criteria: Optional[Dict[str, float]] = None


class CandidatePaginatedResponse(BaseModel):
    """Paginated response untuk list candidates"""

    items: List[CandidateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int