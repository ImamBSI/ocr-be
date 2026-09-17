from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
import uuid

Base = declarative_base()


# ==================== Enums ====================
class UploadStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoringCriteriaType(str, Enum):
    SKILL = "skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    KEYWORD = "keyword"
    CUSTOM = "custom"


# ==================== Models ====================
class Upload(Base):
    """Model untuk file uploads"""
    __tablename__ = "uploads"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)  # in bytes
    status = Column(SQLEnum(UploadStatus), default=UploadStatus.PENDING)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="upload", uselist=False)


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
    skills = Column(JSON, default=list)  # List of skills
    cv_text = Column(Text, nullable=True)  # Full extracted text from CV
    
    # File Information
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(255), nullable=True)
    
    # Metadata
    is_processed = Column(Integer, default=0)  # 0 = not processed, 1 = processed
    processing_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    upload = relationship("Upload", back_populates="candidate")
    scores = relationship("Score", back_populates="candidate", cascade="all, delete-orphan")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ScoringCriteria(Base):
    """Model untuk scoring criteria dalam job requirement"""
    __tablename__ = "scoring_criteria"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("job_requirements.id"), nullable=False)
    
    # Criteria Information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(SQLEnum(ScoringCriteriaType), nullable=False)
    
    # Scoring Configuration
    weight = Column(Float, default=1.0)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    
    # Keywords for matching
    keywords = Column(JSON, default=list)  # List of keywords to match
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("JobRequirement", back_populates="criteria")


class JobRequirement(Base):
    """Model untuk job requirement dengan criteria"""
    __tablename__ = "job_requirements"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Job Information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    criteria = relationship("ScoringCriteria", back_populates="job", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="job", cascade="all, delete-orphan")


class Score(Base):
    """Model untuk scoring results"""
    __tablename__ = "scores"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String(36), ForeignKey("candidates.id"), nullable=False)
    job_id = Column(String(36), ForeignKey("job_requirements.id"), nullable=False)
    
    # Score Information
    score = Column(Float, default=0.0)  # Final score (0-100)
    rank = Column(Integer, nullable=True)  # Ranking among candidates
    
    # Detailed Scoring (JSON)
    matched_criteria = Column(JSON, default=dict)  # Dict of criteria_name: score
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="scores")
    job = relationship("JobRequirement", back_populates="scores")


# ==================== Utility Functions ====================
def get_model_by_name(model_name: str):
    """Get model class by name"""
    models = {
        "Upload": Upload,
        "Candidate": Candidate,
        "ScoringCriteria": ScoringCriteria,
        "JobRequirement": JobRequirement,
        "Score": Score,
    }
    return models.get(model_name)


# ==================== Database Export ====================
__all__ = [
    "Base",
    "Upload",
    "Candidate",
    "ScoringCriteria",
    "JobRequirement",
    "Score",
    "UploadStatus",
    "ScoringCriteriaType",
]