from typing import List, Optional

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = Field(default="created_at")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")


class ErrorResponse(BaseModel):
    detail: str
    status_code: int


class ValidationErrorResponse(BaseModel):
    detail: List[dict]
    status_code: int