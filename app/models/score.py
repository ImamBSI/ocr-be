import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class Score(Base):
    """Model untuk scoring results"""

    __tablename__ = "scores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(
        String(36), ForeignKey("candidates.id"), nullable=False
    )
    job_id = Column(
        String(36), ForeignKey("job_requirements.id"), nullable=False
    )

    score = Column(Float, default=0.0)
    rank = Column(Integer, nullable=True)
    matched_criteria = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    candidate = relationship("Candidate", back_populates="scores")
    job = relationship("JobRequirement", back_populates="scores")