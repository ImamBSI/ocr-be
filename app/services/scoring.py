import logging
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.db.base import Record, Repositories
from app.models.enums import ScoringCriteriaType
from app.services.ai.base import AIProvider, CriteriaScore
from app.services.ai.factory import get_ai_provider
from app.services.ai.score import score_criteria

logger = logging.getLogger(__name__)


class ScoringService:
    @staticmethod
    def _rule_criterion_score(
        candidate: Record, criteria: Record
    ) -> float:
        ctype = getattr(criteria, "type", None)
        keywords = getattr(criteria, "keywords", None) or []

        if ctype == ScoringCriteriaType.SKILL:
            return ScoringService.calculate_skill_match_score(
                candidate.skills, keywords
            )

        if ctype == ScoringCriteriaType.EXPERIENCE:
            return ScoringService.calculate_experience_score(
                candidate.experience_years,
                getattr(criteria, "min_value", None),
                getattr(criteria, "max_value", None),
            )

        if ctype == ScoringCriteriaType.EDUCATION:
            return ScoringService.calculate_education_score(
                candidate.education, keywords
            )

        if ctype == ScoringCriteriaType.KEYWORD:
            return ScoringService.calculate_keyword_match_score(
                candidate.cv_text or "", keywords
            )

        if criteria.type == ScoringCriteriaType.CUSTOM:
            return 50.0

        return 0.0

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
        criteria_min: Optional[float] = None,
        criteria_max: Optional[float] = None,
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
        candidate_education: Optional[str], criteria_keywords: Optional[List[str]] = None
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
    def calculate_keyword_match_score(
        cv_text: Optional[str], keywords: List[str]
    ) -> float:
        if not keywords or not cv_text:
            return 0.0

        text_lower = cv_text.lower()
        matched_keywords = sum(
            1 for keyword in keywords if keyword.lower() in text_lower
        )

        score = (matched_keywords / len(keywords)) * 100
        return min(score, 100.0)

    @staticmethod
    async def score_candidate(
        candidate: Record,
        job_requirement: Record,
        ai_provider: Optional[AIProvider] = None,
    ) -> Tuple[float, Dict[str, float], Dict[str, Optional[str]], float]:
        """
        Hitung skor kandidat.

        Returns:
            (final_score, matched_criteria, rationale, average_confidence)
        """
        logger.info(
            f"Scoring candidate {candidate.id} for job {job_requirement.id}"
        )

        mode = settings.AI_SCORE_MODE.lower()
        use_llm = ai_provider is not None and mode in ("llm", "hybrid")
        ai_scores: Optional[Dict[str, CriteriaScore]] = None
        if use_llm:
            ai_scores = await score_criteria(ai_provider, candidate, job_requirement)

        matched_criteria: Dict[str, float] = {}
        rationale: Dict[str, Optional[str]] = {}
        confidences: List[float] = []

        for criteria in job_requirement.criteria:
            cname = getattr(criteria, "name", "unknown")
            cweight = getattr(criteria, "weight", 1.0) or 1.0

            ai_score: Optional[CriteriaScore] = None
            if ai_scores:
                ai_score = ai_scores.get(cname)

            use_ai_score = bool(
                ai_score
                and (mode == "llm" or ai_score.confidence >= 0.5)
            )

            if use_ai_score:
                criterion_score = ai_score.score
                rationale[cname] = ai_score.evidence
                confidences.append(ai_score.confidence)
            else:
                criterion_score = ScoringService._rule_criterion_score(
                    candidate, criteria
                )
                rationale[cname] = None
                confidences.append(1.0)

            matched_criteria[cname] = criterion_score

        total_weight = sum(
            (getattr(criteria, "weight", 1.0) or 1.0)
            for criteria in job_requirement.criteria
        )
        weighted_score = sum(
            matched_criteria[getattr(criteria, "name", "unknown")]
            * (getattr(criteria, "weight", 1.0) or 1.0)
            for criteria in job_requirement.criteria
        )

        final_score = (
            weighted_score / total_weight if total_weight > 0 else 0.0
        )
        final_score = max(0, min(final_score, 100.0))

        avg_confidence = (
            sum(confidences) / len(confidences) if confidences else 1.0
        )

        logger.info(
            f"Candidate score: {final_score:.2f}, "
            f"confidence: {avg_confidence:.2f}, "
            f"criteria scores: {matched_criteria}"
        )

        return final_score, matched_criteria, rationale, avg_confidence

    @staticmethod
    async def score_and_save(
        repos: Repositories, candidate: Record, job_requirement: Record
    ) -> Record:
        ai_provider = get_ai_provider()
        (
            score_value,
            matched_criteria,
            rationale,
            confidence,
        ) = await ScoringService.score_candidate(
            candidate, job_requirement, ai_provider
        )

        existing_score = repos.scores.get(candidate.id, job_requirement.id)
        if existing_score:
            repos.scores.delete(existing_score.id)

        score_obj = repos.scores.create(
            candidate_id=candidate.id,
            job_id=job_requirement.id,
            score=score_value,
            matched_criteria=matched_criteria,
            rationale=rationale,
            confidence=confidence,
        )

        return score_obj

    @staticmethod
    def get_ranked_candidates(
        repos: Repositories,
        job_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Record]:
        scores = repos.scores.list_by_job(job_id)
        scores.sort(key=lambda s: s.score, reverse=True)

        for rank, score in enumerate(scores, 1):
            repos.scores.set_rank(score.id, rank)

        ranked_scores = scores[offset : offset + limit]
        return [repos.candidates.get(s.candidate_id) for s in ranked_scores]

    @staticmethod
    def get_candidate_ranking(
        repos: Repositories, candidate_id: str, job_id: str
    ) -> int:
        score = repos.scores.get(candidate_id, job_id)
        if score is None:
            return 0
        higher_scores = repos.scores.count_higher(
            candidate_id, job_id, score.score
        )
        return higher_scores + 1


class AnalyticsService:
    """Service untuk analytics dan statistics."""

    @staticmethod
    def get_job_statistics(job_id: str, repos: Repositories) -> Dict:
        scores = repos.scores.list_by_job(job_id)

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
    def get_system_statistics(repos: Repositories) -> Dict:
        total_candidates = repos.candidates.count()
        total_jobs = repos.jobs.count()
        total_uploads = repos.uploads.count()
        total_scores = repos.scores.count()

        avg_score = 0
        highest_score = 0
        lowest_score = 0

        if total_scores > 0:
            scores = [s.score for s in repos.scores.all()]
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
