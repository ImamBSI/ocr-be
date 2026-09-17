from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


# ==================== Enums ====================
class UploadStatusSchema(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoringCriteriaTypeSchema(str, Enum):
    SKILL = "skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    KEYWORD = "keyword"
    CUSTOM = "custom"


# ==================== Upload Schemas ====================
class UploadResponse(BaseModel):
    """Response untuk upload file"""
    id: str
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    status: UploadStatusSchema
    message: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BatchUploadResponse(BaseModel):
    """Response untuk batch upload"""
    total: int
    uploaded: int
    failed: int
    results: List[UploadResponse]


# ==================== Scoring Criteria Schemas ====================
class ScoringCriteriaRequest(BaseModel):
    """Request untuk create/update scoring criteria"""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: ScoringCriteriaTypeSchema
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    keywords: Optional[List[str]] = Field(default=None)


class ScoringCriteriaResponse(ScoringCriteriaRequest):
    """Response untuk scoring criteria"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Job Requirement Schemas ====================
class JobRequirementRequest(BaseModel):
    """Request untuk create/update job requirement"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    criteria: List[ScoringCriteriaRequest] = Field(..., min_length=1)


class JobRequirementResponse(BaseModel):
    """Response untuk job requirement"""
    id: str
    title: str
    description: Optional[str] = None
    criteria: List[ScoringCriteriaResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class JobRequirementListResponse(BaseModel):
    """Response untuk list job requirements"""
    id: str
    title: str
    description: Optional[str] = None
    criteria_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== CV Processing Schemas ====================
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


# ==================== Candidate Schemas ====================
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
    id: str
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    is_processed: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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


# ==================== Scoring Schemas ====================
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


# ==================== Error Schemas ====================
class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    status_code: int


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    detail: List[Dict]
    status_code: int


# ==================== Health & Stats Schemas ====================
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str = "1.0.0"
    database: str


class StatsResponse(BaseModel):
    """System statistics response"""
    total_candidates: int
    total_jobs: int
    total_uploads: int
    total_scores: int
    average_score: Optional[float] = None
    highest_score: Optional[float] = None
    lowest_score: Optional[float] = None


# ==================== Utility Classes ====================
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = Field(default="created_at")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")