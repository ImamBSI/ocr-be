from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import UploadStatus

class UploadResponse(BaseModel):
    """Response untuk upload file"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    status: UploadStatus
    message: Optional[str] = None
    created_at: Optional[datetime] = None


class BatchUploadResponse(BaseModel):
    """Response untuk batch upload"""

    total: int
    uploaded: int
    failed: int
    results: List[UploadResponse]