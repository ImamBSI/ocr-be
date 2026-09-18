import logging
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.enums import ScoringCriteriaType
from app.models.job import JobRequirement, ScoringCriteria
from app.models.score import Score
from app.models.upload import Upload

logger = logging.getLogger(__name__)


class ScoringService:
    """Service untuk scoring candidates berdasarkan job requirements."""

    @staticmethod
    def calculate_skill_match_score(
        candidate_skills: List[str], criteria_keywords: List[str]
    ) -> float:
        if not criteria_keywords:
            return 0.0

        candidate_skills_lower = [s.lower() for s in candidate_skills]
        criteria_lower = [k.lower() for k in criteria_keywords]

        matched = sum(
            1
            for skill in candidate_skills_lower
            if any(keyword in skill or skill in keyword for keyword in criteria_lower)
        )

        score = (matched / len(criteria_keywords)) * 100
        return min(score, 100.0)

    @staticmethod
    def calculate_experience_score(
        candidate_years: int,
        criteria_min: float = None,
        criteria_max: float = None,
    ) -> float:
        if criteria_min is None:
            criteria_min = 0
        if criteria_max is None:
            criteria_max = 20

        if candidate_years < criteria_min:
            score = (candidate_years / criteria_min) * 50 if criteria_min > 0 else 50
        elif candidate_years <= criteria_max:
            score = 100.0
        else:
            excess = candidate_years - criteria_max
            score = 100.0 - (excess * 2)

        return max(0, min(score, 100.0))

    @staticmethod
    def calculate_education_score(
        candidate_education: str, criteria_keywords: List[str] = None
    ) -> float:
        if not candidate_education:
            return 0.0

        if criteria_keywords is None:
            criteria_keywords = ["bachelor", "master", "degree"]

        education_lower = candidate_education.lower()

        degree_scores = {
            "phd": 100,
            "master": 90,
            "bachelor": 85,
            "diploma": 60,
            "degree": 80,
        }

        for degree, score in degree_scores.items():
            if degree in education_lower:
                return float(score)

        if any(keyword.lower() in education_lower for keyword in criteria_keywords):
            return 75.0

        return 50.0

    @staticmethod
    def calculate_keyword_match_score(cv_text: str, keywords: List[str]) -> float:
        if not keywords or not cv_text:
            return 0.0

        text_lower = cv_text.lower()
        matched_keywords = sum(
            1 for keyword in keywords if keyword.lower() in text_lower
        )

        score = (matched_keywords / len(keywords)) * 100
        return min(score, 100.0)

    @staticmethod
    def score_candidate(
        candidate: Candidate,
        job_requirement: JobRequirement,
        db: Session,
    ) -> Tuple[float, Dict[str, float]]:
        logger.info(f"Scoring candidate {candidate.id} for job {job_requirement.id}")

        matched_criteria = {}
        total_weight = 0
        weighted_score = 0

        for criteria in job_requirement.criteria:
            criterion_score = 0

            if criteria.type == ScoringCriteriaType.SKILL:
                keywords = criteria.keywords or []
                criterion_score = ScoringService.calculate_skill_match_score(
                    candidate.skills, keywords
                )

            elif criteria.type == ScoringCriteriaType.EXPERIENCE:
                criterion_score = ScoringService.calculate_experience_score(
                    candidate.experience_years,
                    criteria.min_value,
                    criteria.max_value,
                )

            elif criteria.type == ScoringCriteriaType.EDUCATION:
                keywords = criteria.keywords or []
                criterion_score = ScoringService.calculate_education_score(
                    candidate.education, keywords
                )

            elif criteria.type == ScoringCriteriaType.KEYWORD:
                keywords = criteria.keywords or []
                criterion_score = ScoringService.calculate_keyword_match_score(
                    candidate.cv_text or "", keywords
                )

            elif criteria.type == ScoringCriteriaType.CUSTOM:
                criterion_score = 50.0

            matched_criteria[criteria.name] = criterion_score

            weight = criteria.weight or 1.0
            total_weight += weight
            weighted_score += criterion_score * weight

        final_score = (
            weighted_score / total_weight if total_weight > 0 else 0.0
        )
        final_score = max(0, min(final_score, 100.0))

        logger.info(
            f"Candidate score: {final_score:.2f}, criteria scores: {matched_criteria}"
        )

        return final_score, matched_criteria

    @staticmethod
    def score_and_save(
        candidate: Candidate,
        job_requirement: JobRequirement,
        db: Session,
    ) -> Score:
        score_value, matched_criteria = ScoringService.score_candidate(
            candidate, job_requirement, db
        )

        existing_score = db.query(Score).filter(
            Score.candidate_id == candidate.id,
            Score.job_id == job_requirement.id,
        ).first()

        if existing_score:
            db.delete(existing_score)

        score_obj = Score(
            candidate_id=candidate.id,
            job_id=job_requirement.id,
            score=score_value,
            matched_criteria=matched_criteria,
        )

        db.add(score_obj)
        db.commit()
        db.refresh(score_obj)

        return score_obj

    @staticmethod
    def get_ranked_candidates(
        job_id: str,
        db: Session,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Candidate]:
        scores = db.query(Score).filter(Score.job_id == job_id).order_by(
            Score.score.desc()
        ).all()

        for rank, score in enumerate(scores, 1):
            score.rank = rank

        db.commit()

        ranked_scores = scores[offset : offset + limit]
        return [score.candidate for score in ranked_scores]

    @staticmethod
    def get_candidate_ranking(
        candidate_id: str, job_id: str, db: Session
    ) -> int:
        higher_scores = db.query(Score).filter(
            Score.job_id == job_id,
            Score.score
            > db.query(Score.score)
            .filter(
                Score.candidate_id == candidate_id,
                Score.job_id == job_id,
            )
            .scalar(),
        ).count()

        return higher_scores + 1


class AnalyticsService:
    """Service untuk analytics dan statistics."""

    @staticmethod
    def get_job_statistics(job_id: str, db: Session) -> Dict:
        scores = db.query(Score).filter(Score.job_id == job_id).all()

        if not scores:
            return {
                "total_scored": 0,
                "average_score": 0,
                "highest_score": 0,
                "lowest_score": 0,
                "median_score": 0,
            }

        score_values = sorted(s.score for s in scores)

        return {
            "total_scored": len(score_values),
            "average_score": sum(score_values) / len(score_values),
            "highest_score": max(score_values),
            "lowest_score": min(score_values),
            "median_score": score_values[len(score_values) // 2],
        }

    @staticmethod
    def get_system_statistics(db: Session) -> Dict:
        total_candidates = db.query(Candidate).count()
        total_jobs = db.query(JobRequirement).count()
        total_uploads = db.query(Upload).count()
        total_scores = db.query(Score).count()

        avg_score = 0
        highest_score = 0
        lowest_score = 0

        if total_scores > 0:
            scores = [s.score for s in db.query(Score).all()]
            avg_score = sum(scores) / len(scores)
            highest_score = max(scores)
            lowest_score = min(scores)

        return {
            "total_candidates": total_candidates,
            "total_jobs": total_jobs,
            "total_uploads": total_uploads,
            "total_scores": total_scores,
            "average_score": avg_score,
            "highest_score": highest_score,
            "lowest_score": lowest_score,
        }