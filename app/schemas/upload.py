from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import UploadStatus

class UploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_size: Optional[int] = None
    job_requirement_id: Optional[str] = None
    status: UploadStatus
    message: Optional[str] = None
    created_at: Optional[datetime] = None


class BatchUploadResponse(BaseModel):
    total: int
    uploaded: int
    failed: int
    results: List[UploadResponse]