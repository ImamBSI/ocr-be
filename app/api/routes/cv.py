import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.candidate import Candidate
from app.models.upload import Upload
from app.schemas.cv import (
    CandidatePaginatedResponse,
    CandidateResponse,
    ProcessCVResponse,
)
from app.services.cv import CVService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/{file_id}/process", response_model=ProcessCVResponse)
async def process_cv(
    file_id: str,
    db: Session = Depends(get_db),
):
    """Process CV file - extract text dan parse data."""
    try:
        logger.info(f"Processing CV file: {file_id}")

        upload = db.query(Upload).filter(Upload.id == file_id).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        candidate = CVService.process_upload(db, upload)

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


@router.post("/batch/process")
async def process_cv_batch(
    body: dict,
    db: Session = Depends(get_db),
):
    """Process multiple CVs dalam batch."""
    file_ids = body.get("file_ids", [])

    results = []
    processed_count = 0
    failed_count = 0
    candidates = []

    for file_id in file_ids:
        try:
            upload = db.query(Upload).filter(Upload.id == file_id).first()
            if not upload:
                failed_count += 1
                continue

            candidate = CVService.process_upload(db, upload)
            candidates.append(candidate)
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing file {file_id}: {str(e)}")
            failed_count += 1

    db.commit()

    return {
        "total": len(file_ids),
        "processed": processed_count,
        "failed": failed_count,
        "candidates": [
            CandidateResponse.model_validate(c) for c in candidates
        ],
    }


@router.get("/list", response_model=CandidatePaginatedResponse)
async def list_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """List semua candidates dengan pagination."""
    query = db.query(Candidate)

    total = query.count()

    if sort_by == "name":
        sort_column = Candidate.name
    elif sort_by == "email":
        sort_column = Candidate.email
    elif sort_by == "experience_years":
        sort_column = Candidate.experience_years
    else:
        sort_column = Candidate.created_at

    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * page_size
    candidates = query.offset(offset).limit(page_size).all()

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return CandidatePaginatedResponse(
        items=[CandidateResponse.model_validate(c) for c in candidates],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
):
    """Get single candidate details."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return CandidateResponse.model_validate(candidate)


@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
):
    """Delete candidate."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    db.delete(candidate)
    db.commit()

    return {"message": "Candidate deleted successfully"}