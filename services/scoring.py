import logging
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session

from models import Candidate, JobRequirement, Score, ScoringCriteria
from schemas import ScoringResponse

logger = logging.getLogger(__name__)


# ==================== Scoring Service ====================
class ScoringService:
    """Service untuk scoring candidates berdasarkan job requirements"""
    
    @staticmethod
    def calculate_skill_match_score(candidate_skills: List[str], criteria_keywords: List[str]) -> float:
        """
        Calculate skill match score
        
        Args:
            candidate_skills: List of candidate skills
            criteria_keywords: List of required keywords
            
        Returns:
            Score between 0-100
        """
        if not criteria_keywords:
            return 0.0
        
        candidate_skills_lower = [s.lower() for s in candidate_skills]
        criteria_lower = [k.lower() for k in criteria_keywords]
        
        # Count matching skills
        matched = sum(
            1 for skill in candidate_skills_lower 
            if any(keyword in skill or skill in keyword for keyword in criteria_lower)
        )
        
        # Calculate percentage
        score = (matched / len(criteria_keywords)) * 100
        return min(score, 100.0)
    
    
    @staticmethod
    def calculate_experience_score(candidate_years: int, criteria_min: float = None, criteria_max: float = None) -> float:
        """
        Calculate experience score
        
        Args:
            candidate_years: Years of experience
            criteria_min: Minimum required years
            criteria_max: Maximum expected years
            
        Returns:
            Score between 0-100
        """
        if criteria_min is None:
            criteria_min = 0
        if criteria_max is None:
            criteria_max = 20  # Default max
        
        if candidate_years < criteria_min:
            score = (candidate_years / criteria_min) * 50 if criteria_min > 0 else 50
        elif candidate_years <= criteria_max:
            score = 100.0
        else:
            # Over-qualified: still good but not perfect
            excess = candidate_years - criteria_max
            score = 100.0 - (excess * 2)  # Deduct 2 points per extra year
        
        return max(0, min(score, 100.0))
    
    
    @staticmethod
    def calculate_education_score(candidate_education: str, criteria_keywords: List[str] = None) -> float:
        """
        Calculate education score
        
        Args:
            candidate_education: Candidate education string
            criteria_keywords: Required education keywords
            
        Returns:
            Score between 0-100
        """
        if not candidate_education:
            return 0.0
        
        if criteria_keywords is None:
            criteria_keywords = ['bachelor', 'master', 'degree']
        
        education_lower = candidate_education.lower()
        
        # Check for degree levels
        degree_scores = {
            'phd': 100,
            'master': 90,
            'bachelor': 85,
            'diploma': 60,
            'degree': 80,
        }
        
        for degree, score in degree_scores.items():
            if degree in education_lower:
                return float(score)
        
        # Check for keywords
        if any(keyword.lower() in education_lower for keyword in criteria_keywords):
            return 75.0
        
        return 50.0  # Default score for any education
    
    
    @staticmethod
    def calculate_keyword_match_score(cv_text: str, keywords: List[str]) -> float:
        """
        Calculate keyword match score from CV text
        
        Args:
            cv_text: Full CV text
            keywords: Keywords to search for
            
        Returns:
            Score between 0-100
        """
        if not keywords or not cv_text:
            return 0.0
        
        text_lower = cv_text.lower()
        matched_keywords = sum(
            1 for keyword in keywords
            if keyword.lower() in text_lower
        )
        
        score = (matched_keywords / len(keywords)) * 100
        return min(score, 100.0)
    
    
    @staticmethod
    def score_candidate(
        candidate: Candidate,
        job_requirement: JobRequirement,
        db: Session
    ) -> Tuple[float, Dict[str, float]]:
        """
        Score candidate untuk job requirement
        
        Args:
            candidate: Candidate object
            job_requirement: JobRequirement object
            db: Database session
            
        Returns:
            Tuple of (final_score, matched_criteria_dict)
        """
        logger.info(f"Scoring candidate {candidate.id} for job {job_requirement.id}")
        
        matched_criteria = {}
        total_weight = 0
        weighted_score = 0
        
        # Score each criteria
        for criteria in job_requirement.criteria:
            criterion_score = 0
            
            if criteria.type == "skill":
                # Score based on skills
                keywords = criteria.keywords or []
                criterion_score = ScoringService.calculate_skill_match_score(
                    candidate.skills,
                    keywords
                )
            
            elif criteria.type == "experience":
                # Score based on experience
                criterion_score = ScoringService.calculate_experience_score(
                    candidate.experience_years,
                    criteria.min_value,
                    criteria.max_value
                )
            
            elif criteria.type == "education":
                # Score based on education
                keywords = criteria.keywords or []
                criterion_score = ScoringService.calculate_education_score(
                    candidate.education,
                    keywords
                )
            
            elif criteria.type == "keyword":
                # Score based on keyword matching in CV
                keywords = criteria.keywords or []
                criterion_score = ScoringService.calculate_keyword_match_score(
                    candidate.cv_text or "",
                    keywords
                )
            
            elif criteria.type == "custom":
                # Custom scoring: default to 50 (needs implementation)
                criterion_score = 50.0
            
            # Store score for this criteria
            matched_criteria[criteria.name] = criterion_score
            
            # Add weighted score
            weight = criteria.weight or 1.0
            total_weight += weight
            weighted_score += criterion_score * weight
        
        # Calculate final score
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0
        
        # Ensure score is between 0-100
        final_score = max(0, min(final_score, 100.0))
        
        logger.info(f"Candidate score: {final_score:.2f}, criteria scores: {matched_criteria}")
        
        return final_score, matched_criteria
    
    
    @staticmethod
    def score_and_save(
        candidate: Candidate,
        job_requirement: JobRequirement,
        db: Session
    ) -> Score:
        """
        Score candidate dan save ke database
        
        Args:
            candidate: Candidate object
            job_requirement: JobRequirement object
            db: Database session
            
        Returns:
            Score object
        """
        # Calculate score
        score_value, matched_criteria = ScoringService.score_candidate(
            candidate,
            job_requirement,
            db
        )
        
        # Delete existing score if any
        existing_score = db.query(Score).filter(
            Score.candidate_id == candidate.id,
            Score.job_id == job_requirement.id
        ).first()
        
        if existing_score:
            db.delete(existing_score)
        
        # Create new score
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
        offset: int = 0
    ) -> List[Candidate]:
        """
        Get ranked candidates untuk specific job
        
        Args:
            job_id: Job ID
            db: Database session
            limit: Number of results
            offset: Pagination offset
            
        Returns:
            List of ranked candidates
        """
        # Query scores ordered by score descending
        scores = db.query(Score).filter(
            Score.job_id == job_id
        ).order_by(Score.score.desc()).all()
        
        # Update ranking
        for rank, score in enumerate(scores, 1):
            score.rank = rank
        
        db.commit()
        
        # Get candidates with pagination
        ranked_scores = scores[offset:offset + limit]
        candidates = [score.candidate for score in ranked_scores]
        
        return candidates
    
    
    @staticmethod
    def get_candidate_ranking(
        candidate_id: str,
        job_id: str,
        db: Session
    ) -> int:
        """
        Get ranking position for candidate
        
        Args:
            candidate_id: Candidate ID
            job_id: Job ID
            db: Database session
            
        Returns:
            Ranking position (1-based)
        """
        # Count candidates with higher score
        higher_scores = db.query(Score).filter(
            Score.job_id == job_id,
            Score.score > db.query(Score.score).filter(
                Score.candidate_id == candidate_id,
                Score.job_id == job_id
            ).scalar()
        ).count()
        
        return higher_scores + 1


# ==================== Analytics Service ====================
class AnalyticsService:
    """Service untuk analytics dan statistics"""
    
    @staticmethod
    def get_job_statistics(job_id: str, db: Session) -> Dict:
        """
        Get statistics untuk job requirement
        
        Args:
            job_id: Job ID
            db: Database session
            
        Returns:
            Dictionary dengan statistics
        """
        scores = db.query(Score).filter(Score.job_id == job_id).all()
        
        if not scores:
            return {
                'total_scored': 0,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0,
                'median_score': 0,
            }
        
        score_values = [s.score for s in scores]
        score_values.sort()
        
        return {
            'total_scored': len(score_values),
            'average_score': sum(score_values) / len(score_values),
            'highest_score': max(score_values),
            'lowest_score': min(score_values),
            'median_score': score_values[len(score_values) / 2],
        }
    
    
    @staticmethod
    def get_system_statistics(db: Session) -> Dict:
        """
        Get overall system statistics
        
        Args:
            db: Database session
            
        Returns:
            Dictionary dengan system stats
        """
        total_candidates = db.query(Candidate).count()
        total_jobs = db.query(JobRequirement).count()
        total_scores = db.query(Score).count()
        
        avg_score = 0
        highest_score = 0
        lowest_score = 0
        
        if total_scores > 0:
            score_data = db.query(Score).all()
            scores = [s.score for s in score_data]
            avg_score = sum(scores) / len(scores)
            highest_score = max(scores)
            lowest_score = min(scores)
        
        return {
            'total_candidates': total_candidates,
            'total_jobs': total_jobs,
            'total_scores': total_scores,
            'average_score': avg_score,
            'highest_score': highest_score,
            'lowest_score': lowest_score,
        }