from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ScoringCriteriaType


class ScoringCriteriaRequest(BaseModel):
    """Request untuk create/update scoring criteria"""

    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: ScoringCriteriaType
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    keywords: Optional[List[str]] = Field(default=None)


class ScoringCriteriaResponse(ScoringCriteriaRequest):
    """Response untuk scoring criteria"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class JobRequirementRequest(BaseModel):
    """Request untuk create/update job requirement"""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    criteria: List[ScoringCriteriaRequest] = Field(..., min_length=1)


class JobRequirementResponse(BaseModel):
    """Response untuk job requirement"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    criteria: List[ScoringCriteriaResponse]
    created_at: datetime
    updated_at: datetime


class JobRequirementListResponse(BaseModel):
    """Response untuk list job requirements"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    criteria_count: int
    created_at: datetime