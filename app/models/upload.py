import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import UploadStatus


class Upload(Base):
    """Model untuk file uploads"""

    __tablename__ = "uploads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    status = Column(SQLEnum(UploadStatus), default=UploadStatus.PENDING)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    candidate = relationship(
        "Candidate", back_populates="upload", uselist=False
    )