from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import logging

from database import get_db
from models import Candidate, Upload
from schemas import (
    ProcessCVResponse,
    CandidateResponse,
    CandidatePaginatedResponse,
    CandidateDetailResponse,
)
from services.ocr import CVProcessingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cv", tags=["cv"])


# ==================== Helper Functions ====================
def get_file_type(file_path: str) -> str:
    """Extract file type from path"""
    return file_path.split('.')[-1].lower()


# ==================== Routes ====================
@router.post("/{file_id}/process", response_model=ProcessCVResponse)
async def process_cv(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    Process CV file - Extract text dan parse data
    
    Returns:
        Processed CV data
    """
    try:
        logger.info(f"Processing CV file: {file_id}")
        
        # Get upload record
        upload = db.query(Upload).filter(Upload.id == file_id).first()
        
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        if not upload.file_path:
            raise HTTPException(status_code=400, detail="File path not found")
        
        # Get file type
        file_type = get_file_type(upload.file_path)
        
        # Process CV
        parsed_data = CVProcessingService.process_cv_file(upload.file_path, file_type)
        
        # Check if candidate already exists
        existing_candidate = db.query(Candidate).filter(
            Candidate.email == parsed_data.get('email')
        ).first()
        
        if existing_candidate:
            # Update existing candidate
            existing_candidate.name = parsed_data.get('name', existing_candidate.name)
            existing_candidate.phone = parsed_data.get('phone', existing_candidate.phone)
            existing_candidate.experience_years = parsed_data.get('experience_years', 0)
            existing_candidate.skills = parsed_data.get('skills', [])
            existing_candidate.education = parsed_data.get('education')
            existing_candidate.cv_text = parsed_data.get('cv_text')
            existing_candidate.file_name = upload.file_name
            existing_candidate.file_path = upload.file_path
            existing_candidate.is_processed = 1
            
            candidate = existing_candidate
            logger.info(f"Updated existing candidate: {candidate.id}")
        
        else:
            # Create new candidate
            candidate = Candidate(
                upload_id=file_id,
                name=parsed_data.get('name', 'Unknown'),
                email=parsed_data.get('email', ''),
                phone=parsed_data.get('phone'),
                experience_years=parsed_data.get('experience_years', 0),
                skills=parsed_data.get('skills', []),
                education=parsed_data.get('education'),
                cv_text=parsed_data.get('cv_text'),
                file_name=upload.file_name,
                file_path=upload.file_path,
                is_processed=1,
            )
            
            db.add(candidate)
            logger.info(f"Created new candidate: {candidate.id}")
        
        db.commit()
        db.refresh(candidate)
        
        return ProcessCVResponse(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            experience_years=candidate.experience_years,
            skills=candidate.skills,
            education=candidate.education,
            cv_text=candidate.cv_text,
            status="success"
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing CV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/process")
async def process_cv_batch(
    body: dict,
    db: Session = Depends(get_db)
):
    """
    Process multiple CVs in batch
    """
    file_ids = body.get('file_ids', [])
    
    results = []
    processed_count = 0
    failed_count = 0
    candidates = []
    
    for file_id in file_ids:
        try:
            # Get upload
            upload = db.query(Upload).filter(Upload.id == file_id).first()
            if not upload:
                failed_count += 1
                continue
            
            # Process CV
            file_type = get_file_type(upload.file_path)
            parsed_data = CVProcessingService.process_cv_file(upload.file_path, file_type)
            
            # Create or update candidate
            candidate = db.query(Candidate).filter(
                Candidate.email == parsed_data.get('email')
            ).first()
            
            if not candidate:
                candidate = Candidate(
                    upload_id=file_id,
                    name=parsed_data.get('name', 'Unknown'),
                    email=parsed_data.get('email', ''),
                    phone=parsed_data.get('phone'),
                    experience_years=parsed_data.get('experience_years', 0),
                    skills=parsed_data.get('skills', []),
                    education=parsed_data.get('education'),
                    cv_text=parsed_data.get('cv_text'),
                    file_name=upload.file_name,
                    file_path=upload.file_path,
                    is_processed=1,
                )
                db.add(candidate)
            else:
                candidate.is_processed = 1
            
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
        "candidates": [CandidateResponse.model_validate(c) for c in candidates],
    }


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db)
):
    """
    Get single candidate details
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    return CandidateResponse.model_validate(candidate)


@router.get("/list", response_model=CandidatePaginatedResponse)
async def list_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    List all candidates with pagination
    """
    # Build query
    query = db.query(Candidate)
    
    # Get total
    total = query.count()
    
    # Sort
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
    
    # Paginate
    offset = (page - 1) * page_size
    candidates = query.offset(offset).limit(page_size).all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return CandidatePaginatedResponse(
        items=[CandidateResponse.model_validate(c) for c in candidates],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete candidate
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    db.delete(candidate)
    db.commit()
    
    return {"message": "Candidate deleted successfully"}