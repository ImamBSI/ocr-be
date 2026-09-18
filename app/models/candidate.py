import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class Candidate(Base):
    """Model untuk candidate/CV data"""

    __tablename__ = "candidates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_id = Column(String(36), ForeignKey("uploads.id"), nullable=True)

    # Personal Information
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)

    # Professional Information
    experience_years = Column(Integer, default=0)
    education = Column(String(255), nullable=True)

    # Extracted Data (JSON)
    skills = Column(JSON, default=list)
    cv_text = Column(Text, nullable=True)

    # File Information
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(255), nullable=True)

    # Metadata
    is_processed = Column(Integer, default=0)
    processing_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    upload = relationship("Upload", back_populates="candidate")
    scores = relationship(
        "Score", back_populates="candidate", cascade="all, delete-orphan"
    )