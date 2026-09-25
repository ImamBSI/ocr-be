import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repos
from app.db.base import Repositories
from app.schemas.scoring import (
    BatchScoringRequest,
    BatchScoringResponse,
    RankedCandidateResponse,
    ScoringRequest,
    ScoringResponse,
)
from app.services.scoring import ScoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/score", tags=["scoring"])


def _build_scoring_response(score_obj, rank) -> ScoringResponse:
    return ScoringResponse(
        id=score_obj.id,
        candidate_id=score_obj.candidate_id,
        score=score_obj.score,
        rank=rank,
        matched_criteria=score_obj.matched_criteria,
        status="success",
        created_at=score_obj.created_at,
    )


@router.post("/batch", response_model=BatchScoringResponse)
async def score_batch(
    body: BatchScoringRequest,
    repos: Repositories = Depends(get_repos),
):
    """Score multiple candidates dalam batch."""
    logger.info(f"Batch scoring {len(body.candidate_ids)} candidates")

    job = repos.jobs.get(body.job_requirement_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job requirement not found")

    results = []
    scored_count = 0
    failed_count = 0

    for candidate_id in body.candidate_ids:
        try:
            candidate = repos.candidates.get(candidate_id)
            if not candidate:
                failed_count += 1
                continue

            score_obj = ScoringService.score_and_save(repos, candidate, job)
            ranking = ScoringService.get_candidate_ranking(
                repos, candidate_id, body.job_requirement_id
            )
            results.append(_build_scoring_response(score_obj, ranking))
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


@router.post("/{candidate_id}", response_model=ScoringResponse)
async def score_candidate(
    candidate_id: str,
    body: ScoringRequest,
    repos: Repositories = Depends(get_repos),
):
    """Score single candidate untuk job requirement."""
    try:
        logger.info(
            f"Scoring candidate {candidate_id} for job {body.job_requirement_id}"
        )

        candidate = repos.candidates.get(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        job = repos.jobs.get(body.job_requirement_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")

        score_obj = ScoringService.score_and_save(repos, candidate, job)
        ranking = ScoringService.get_candidate_ranking(
            repos, candidate_id, body.job_requirement_id
        )

        return _build_scoring_response(score_obj, ranking)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error scoring candidate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranked/{job_id}", response_model=list[RankedCandidateResponse])
async def get_ranked_candidates(
    job_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repos: Repositories = Depends(get_repos),
):
    """Get ranked candidates untuk job."""
    try:
        job = repos.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job requirement not found")

        candidates = ScoringService.get_ranked_candidates(repos, job_id, limit, offset)

        response = []
        for candidate in candidates:
            if not candidate:
                continue
            score_obj = repos.scores.get(candidate.id, job_id)
            if score_obj:
                response.append(
                    RankedCandidateResponse(
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
                )

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
    repos: Repositories = Depends(get_repos),
):
    """Get detailed score untuk candidate."""
    score_obj = repos.scores.get(candidate_id, job_id)

    if not score_obj:
        raise HTTPException(status_code=404, detail="Score not found")

    return _build_scoring_response(score_obj, score_obj.rank)