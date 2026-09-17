from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import logging

from database import get_db
from models import Candidate, JobRequirement, Score
from schemas import (
    ScoringRequest,
    BatchScoringRequest,
    ScoringResponse,
    BatchScoringResponse,
    RankedCandidateResponse,
    CandidateDetailResponse,
)
from services.scoring import ScoringService, AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/score", tags=["scoring"])


# ==================== Routes ====================
@router.post("/{candidate_id}", response_model=ScoringResponse)
async def score_candidate(
    candidate_id: str,
    body: ScoringRequest,
    db: Session = Depends(get_db)
):
    """
    Score single candidate for job requirement
    """
    try:
        logger.info(f"Scoring candidate {candidate_id} for job {body.job_requirement_id}")
        
        # Get candidate
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Get job requirement
        job = db.query(JobRequirement).filter(
            JobRequirement.id == body.job_requirement_id
        ).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")
        
        # Score and save
        score_obj = ScoringService.score_and_save(candidate, job, db)
        
        # Get ranking
        ranking = ScoringService.get_candidate_ranking(candidate_id, body.job_requirement_id, db)
        
        return ScoringResponse(
            id=score_obj.id,
            candidate_id=score_obj.candidate_id,
            score=score_obj.score,
            rank=ranking,
            matched_criteria=score_obj.matched_criteria,
            status="success",
            created_at=score_obj.created_at,
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error scoring candidate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchScoringResponse)
async def score_batch(
    body: BatchScoringRequest,
    db: Session = Depends(get_db)
):
    """
    Score multiple candidates in batch
    """
    logger.info(f"Batch scoring {len(body.candidate_ids)} candidates")
    
    # Get job requirement
    job = db.query(JobRequirement).filter(
        JobRequirement.id == body.job_requirement_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job requirement not found")
    
    results = []
    scored_count = 0
    failed_count = 0
    
    for candidate_id in body.candidate_ids:
        try:
            # Get candidate
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not candidate:
                failed_count += 1
                continue
            
            # Score and save
            score_obj = ScoringService.score_and_save(candidate, job, db)
            ranking = ScoringService.get_candidate_ranking(candidate_id, body.job_requirement_id, db)
            
            results.append(ScoringResponse(
                id=score_obj.id,
                candidate_id=score_obj.candidate_id,
                score=score_obj.score,
                rank=ranking,
                matched_criteria=score_obj.matched_criteria,
                status="success",
                created_at=score_obj.created_at,
            ))
            
            scored_count += 1
            
        except Exception as e:
            logger.error(f"Error scoring candidate {candidate_id}: {str(e)}")
            failed_count += 1
    
    return BatchScoringResponse(
        total=len(body.candidate_ids),
        scored=scored_count,
        failed=failed_count,
        results=results,
    )


@router.get("/ranked/{job_id}", response_model=list[RankedCandidateResponse])
async def get_ranked_candidates(
    job_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get ranked candidates for job
    """
    try:
        # Verify job exists
        job = db.query(JobRequirement).filter(JobRequirement.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")
        
        # Get ranked candidates
        candidates = ScoringService.get_ranked_candidates(job_id, db, limit, offset)
        
        # Build response
        response = []
        for candidate in candidates:
            score_obj = db.query(Score).filter(
                Score.candidate_id == candidate.id,
                Score.job_id == job_id
            ).first()
            
            if score_obj:
                ranked_candidate = RankedCandidateResponse(
                    id=candidate.id,
                    name=candidate.name,
                    email=candidate.email,
                    phone=candidate.phone,
                    experience_years=candidate.experience_years,
                    skills=candidate.skills,
                    education=candidate.education,
                    cv_text=candidate.cv_text,
                    file_name=candidate.file_name,
                    file_path=candidate.file_path,
                    is_processed=bool(candidate.is_processed),
                    created_at=candidate.created_at,
                    updated_at=candidate.updated_at,
                    score=score_obj.score,
                    ranking=score_obj.rank or 0,
                    matched_criteria=score_obj.matched_criteria,
                )
                response.append(ranked_candidate)
        
        return response
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting ranked candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{candidate_id}/details", response_model=ScoringResponse)
async def get_score_details(
    candidate_id: str,
    job_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get detailed score for candidate
    """
    score_obj = db.query(Score).filter(
        Score.candidate_id == candidate_id,
        Score.job_id == job_id
    ).first()
    
    if not score_obj:
        raise HTTPException(status_code=404, detail="Score not found")
    
    return ScoringResponse(
        id=score_obj.id,
        candidate_id=score_obj.candidate_id,
        score=score_obj.score,
        rank=score_obj.rank,
        matched_criteria=score_obj.matched_criteria,
        status="success",
        created_at=score_obj.created_at,
    )