import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import ScoringCriteriaType


class ScoringCriteria(Base):
    """Model untuk scoring criteria dalam job requirement"""

    __tablename__ = "scoring_criteria"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("job_requirements.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(SQLEnum(ScoringCriteriaType), nullable=False)

    weight = Column(Float, default=1.0)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    keywords = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    job = relationship("JobRequirement", back_populates="criteria")


class JobRequirement(Base):
    """Model untuk job requirement dengan criteria"""

    __tablename__ = "job_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    criteria = relationship(
        "ScoringCriteria",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    scores = relationship(
        "Score", back_populates="job", cascade="all, delete-orphan"
    )