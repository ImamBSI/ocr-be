import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repos
from app.db.base import Repositories
from app.schemas.cv import (
    CandidatePaginatedResponse,
    CandidateResponse,
    ProcessCVResponse,
)
from app.services.cv import CVService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/batch/process")
async def process_cv_batch(
    body: dict,
    repos: Repositories = Depends(get_repos),
):
    """Process multiple CVs dalam batch."""
    file_ids = body.get("file_ids", [])

    results = []
    processed_count = 0
    failed_count = 0
    candidates = []

    for file_id in file_ids:
        try:
            upload = repos.uploads.get(file_id)
            if not upload:
                failed_count += 1
                continue

            candidate = CVService.process_upload(repos, upload)
            candidates.append(candidate)
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing file {file_id}: {str(e)}")
            failed_count += 1

    return {
        "total": len(file_ids),
        "processed": processed_count,
        "failed": failed_count,
        "candidates": [
            CandidateResponse.model_validate(c) for c in candidates
        ],
    }


@router.post("/{file_id}/process", response_model=ProcessCVResponse)
async def process_cv(
    file_id: str,
    repos: Repositories = Depends(get_repos),
):
    """Process CV file - extract text dan parse data."""
    try:
        logger.info(f"Processing CV file: {file_id}")

        upload = repos.uploads.get(file_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        candidate = CVService.process_upload(repos, upload)

        return ProcessCVResponse(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            experience_years=candidate.experience_years,
            skills=candidate.skills,
            education=candidate.education,
            cv_text=candidate.cv_text,
            status="success",
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing CV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=CandidatePaginatedResponse)
async def list_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    repos: Repositories = Depends(get_repos),
):
    """List semua candidates dengan pagination."""
    offset = (page - 1) * page_size
    total, items = repos.candidates.list(
        sort_by=sort_by,
        sort_order=sort_order,
        offset=offset,
        limit=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return CandidatePaginatedResponse(
        items=[CandidateResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    repos: Repositories = Depends(get_repos),
):
    """Get single candidate details."""
    candidate = repos.candidates.get(candidate_id)

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return CandidateResponse.model_validate(candidate)


@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: str,
    repos: Repositories = Depends(get_repos),
):
    """Delete candidate."""
    candidate = repos.candidates.get(candidate_id)

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    repos.candidates.delete(candidate_id)

    return {"message": "Candidate deleted successfully"}