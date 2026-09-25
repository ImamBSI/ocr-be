import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repos
from app.db.base import Repositories
from app.schemas.job import (
    JobRequirementRequest,
    JobRequirementResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _criteria_dump(body: JobRequirementRequest) -> List[dict]:
    return [c.model_dump() for c in body.criteria]


@router.get("", response_model=List[JobRequirementResponse])
async def list_jobs(repos: Repositories = Depends(get_repos)):
    """List semua job requirements."""
    return [
        JobRequirementResponse.model_validate(job) for job in repos.jobs.list()
    ]


@router.post("", response_model=JobRequirementResponse)
async def create_job(
    body: JobRequirementRequest,
    repos: Repositories = Depends(get_repos),
):
    """Create job requirement baru."""
    try:
        logger.info(f"Creating job requirement: {body.title}")

        job = repos.jobs.create(
            title=body.title,
            description=body.description,
            criteria=_criteria_dump(body),
        )

        logger.info(f"Job created: {job.id}")
        return JobRequirementResponse.model_validate(job)

    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobRequirementResponse)
async def get_job(
    job_id: str,
    repos: Repositories = Depends(get_repos),
):
    """Get single job requirement."""
    job = repos.jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job requirement not found")

    return JobRequirementResponse.model_validate(job)


@router.put("/{job_id}", response_model=JobRequirementResponse)
async def update_job(
    job_id: str,
    body: JobRequirementRequest,
    repos: Repositories = Depends(get_repos),
):
    """Update job requirement."""
    try:
        logger.info(f"Updating job: {job_id}")

        job = repos.jobs.update(
            job_id,
            title=body.title,
            description=body.description,
            criteria=_criteria_dump(body),
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")

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
    repos: Repositories = Depends(get_repos),
):
    """Delete job requirement."""
    try:
        job = repos.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")

        repos.jobs.delete(job_id)

        logger.info(f"Job deleted: {job_id}")
        return {"message": "Job requirement deleted successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))