import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.job import JobRequirement, ScoringCriteria
from app.schemas.job import (
    JobRequirementListResponse,
    JobRequirementRequest,
    JobRequirementResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _build_criteria(job: JobRequirement, body: JobRequirementRequest):
    for criterion_data in body.criteria:
        job.criteria.append(
            ScoringCriteria(
                name=criterion_data.name,
                description=criterion_data.description,
                type=criterion_data.type,
                weight=criterion_data.weight,
                min_value=criterion_data.min_value,
                max_value=criterion_data.max_value,
                keywords=criterion_data.keywords or [],
            )
        )


@router.get("", response_model=List[JobRequirementListResponse])
async def list_jobs(db: Session = Depends(get_db)):
    """List semua job requirements."""
    jobs = (
        db.query(JobRequirement)
        .order_by(JobRequirement.created_at.desc())
        .all()
    )

    return [
        JobRequirementListResponse(
            id=job.id,
            title=job.title,
            description=job.description,
            criteria_count=len(job.criteria),
            created_at=job.created_at,
        )
        for job in jobs
    ]


@router.post("", response_model=JobRequirementResponse)
async def create_job(
    body: JobRequirementRequest,
    db: Session = Depends(get_db),
):
    """Create job requirement baru."""
    try:
        logger.info(f"Creating job requirement: {body.title}")

        job = JobRequirement(title=body.title, description=body.description)
        _build_criteria(job, body)

        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"Job created: {job.id}")
        return JobRequirementResponse.model_validate(job)

    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobRequirementResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Get single job requirement."""
    job = db.query(JobRequirement).filter(JobRequirement.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job requirement not found")

    return JobRequirementResponse.model_validate(job)


@router.put("/{job_id}", response_model=JobRequirementResponse)
async def update_job(
    job_id: str,
    body: JobRequirementRequest,
    db: Session = Depends(get_db),
):
    """Update job requirement."""
    try:
        logger.info(f"Updating job: {job_id}")

        job = db.query(JobRequirement).filter(JobRequirement.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")

        job.title = body.title
        job.description = body.description

        db.query(ScoringCriteria).filter(ScoringCriteria.job_id == job_id).delete()

        _build_criteria(job, body)

        db.commit()
        db.refresh(job)

        logger.info(f"Job updated: {job.id}")
        return JobRequirementResponse.model_validate(job)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Delete job requirement."""
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