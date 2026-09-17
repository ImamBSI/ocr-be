from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from typing import List

from database import get_db
from models import JobRequirement, ScoringCriteria
from schemas import (
    JobRequirementRequest,
    JobRequirementResponse,
    JobRequirementListResponse,
    ScoringCriteriaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ==================== Routes ====================
@router.get("", response_model=List[JobRequirementListResponse])
async def list_jobs(db: Session = Depends(get_db)):
    """
    List all job requirements
    """
    jobs = db.query(JobRequirement).order_by(JobRequirement.created_at.desc()).all()
    
    response = []
    for job in jobs:
        response.append(JobRequirementListResponse(
            id=job.id,
            title=job.title,
            description=job.description,
            criteria_count=len(job.criteria),
            created_at=job.created_at,
        ))
    
    return response


@router.post("", response_model=JobRequirementResponse)
async def create_job(
    body: JobRequirementRequest,
    db: Session = Depends(get_db)
):
    """
    Create new job requirement
    """
    try:
        logger.info(f"Creating job requirement: {body.title}")
        
        # Create job
        job = JobRequirement(
            title=body.title,
            description=body.description,
        )
        
        # Add criteria
        for criterion_data in body.criteria:
            criterion = ScoringCriteria(
                job_id=job.id,
                name=criterion_data.name,
                description=criterion_data.description,
                type=criterion_data.type,
                weight=criterion_data.weight,
                min_value=criterion_data.min_value,
                max_value=criterion_data.max_value,
                keywords=criterion_data.keywords or [],
            )
            job.criteria.append(criterion)
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Job created: {job.id}")
        
        # Build response
        return JobRequirementResponse(
            id=job.id,
            title=job.title,
            description=job.description,
            criteria=[
                ScoringCriteriaResponse(
                    id=c.id,
                    name=c.name,
                    description=c.description,
                    type=c.type,
                    weight=c.weight,
                    min_value=c.min_value,
                    max_value=c.max_value,
                    keywords=c.keywords,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in job.criteria
            ],
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobRequirementResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get single job requirement
    """
    job = db.query(JobRequirement).filter(JobRequirement.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job requirement not found")
    
    return JobRequirementResponse(
        id=job.id,
        title=job.title,
        description=job.description,
        criteria=[
            ScoringCriteriaResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                type=c.type,
                weight=c.weight,
                min_value=c.min_value,
                max_value=c.max_value,
                keywords=c.keywords,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in job.criteria
        ],
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.put("/{job_id}", response_model=JobRequirementResponse)
async def update_job(
    job_id: str,
    body: JobRequirementRequest,
    db: Session = Depends(get_db)
):
    """
    Update job requirement
    """
    try:
        logger.info(f"Updating job: {job_id}")
        
        job = db.query(JobRequirement).filter(JobRequirement.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")
        
        # Update basic info
        job.title = body.title
        job.description = body.description
        
        # Delete old criteria
        db.query(ScoringCriteria).filter(ScoringCriteria.job_id == job_id).delete()
        
        # Add new criteria
        for criterion_data in body.criteria:
            criterion = ScoringCriteria(
                job_id=job.id,
                name=criterion_data.name,
                description=criterion_data.description,
                type=criterion_data.type,
                weight=criterion_data.weight,
                min_value=criterion_data.min_value,
                max_value=criterion_data.max_value,
                keywords=criterion_data.keywords or [],
            )
            job.criteria.append(criterion)
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Job updated: {job.id}")
        
        return JobRequirementResponse(
            id=job.id,
            title=job.title,
            description=job.description,
            criteria=[
                ScoringCriteriaResponse(
                    id=c.id,
                    name=c.name,
                    description=c.description,
                    type=c.type,
                    weight=c.weight,
                    min_value=c.min_value,
                    max_value=c.max_value,
                    keywords=c.keywords,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in job.criteria
            ],
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete job requirement
    """
    try:
        job = db.query(JobRequirement).filter(JobRequirement.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")
        
        db.delete(job)
        db.commit()
        
        logger.info(f"Job deleted: {job_id}")
        
        return {"message": "Job requirement deleted successfully"}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))