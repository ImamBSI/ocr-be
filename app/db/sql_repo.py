from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.db.base import (
    CandidateRepository,
    JobRepository,
    Record,
    ScoreRepository,
    UploadRepository,
)
from app.models.candidate import Candidate
from app.models.enums import ScoringCriteriaType
from app.models.job import JobRequirement, ScoringCriteria
from app.models.score import Score
from app.models.upload import Upload


def _wrap(record):
    return record  # ORM objects sudah punya attribute access


class SqlUploadRepository(UploadRepository):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def _session(self) -> Session:
        return self.session_factory()

    def get(self, upload_id: str) -> Optional[Record]:
        db = self._session()
        try:
            return db.query(Upload).filter(Upload.id == upload_id).first()
        finally:
            db.close()

    def create(
        self, *, file_name: str, file_path: str, file_size: int, status
    ) -> Record:
        db = self._session()
        try:
            upload = Upload(
                file_name=file_name,
                file_path=file_path,
                file_size=file_size,
                status=status,
            )
            db.add(upload)
            db.commit()
            db.refresh(upload)
            return upload
        finally:
            db.close()

    def delete(self, upload_id: str) -> bool:
        db = self._session()
        try:
            upload = db.query(Upload).filter(Upload.id == upload_id).first()
            if not upload:
                return False
            db.delete(upload)
            db.commit()
            return True
        finally:
            db.close()

    def count(self) -> int:
        db = self._session()
        try:
            return db.query(Upload).count()
        finally:
            db.close()


class SqlCandidateRepository(CandidateRepository):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def _session(self) -> Session:
        return self.session_factory()

    def get(self, candidate_id: str) -> Optional[Record]:
        db = self._session()
        try:
            return db.query(Candidate).filter(Candidate.id == candidate_id).first()
        finally:
            db.close()

    def get_by_email(self, email: str) -> Optional[Record]:
        db = self._session()
        try:
            return db.query(Candidate).filter(Candidate.email == email).first()
        finally:
            db.close()

    def create(self, **data) -> Record:
        db = self._session()
        try:
            candidate = Candidate(**data)
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
            return candidate
        finally:
            db.close()

    def update(self, candidate_id: str, **changes) -> Optional[Record]:
        db = self._session()
        try:
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not candidate:
                return None
            for key, value in changes.items():
                setattr(candidate, key, value)
            db.commit()
            db.refresh(candidate)
            return candidate
        finally:
            db.close()

    def delete(self, candidate_id: str) -> bool:
        db = self._session()
        try:
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not candidate:
                return False
            db.delete(candidate)
            db.commit()
            return True
        finally:
            db.close()

    def count(self) -> int:
        db = self._session()
        try:
            return db.query(Candidate).count()
        finally:
            db.close()

    def list(
        self,
        *,
        sort_by: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> Tuple[int, List[Record]]:
        db = self._session()
        try:
            query = db.query(Candidate)
            total = query.count()

            sort_column = {
                "name": Candidate.name,
                "email": Candidate.email,
                "experience_years": Candidate.experience_years,
            }.get(sort_by, Candidate.created_at)

            if sort_order == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            items = query.offset(offset).limit(limit).all()
            return total, items
        finally:
            db.close()


class SqlJobRepository(JobRepository):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def _session(self) -> Session:
        return self.session_factory()

    @staticmethod
    def _build_criteria(job: JobRequirement, criteria: List[dict]) -> None:
        job.criteria = [
            ScoringCriteria(
                name=c.get("name"),
                description=c.get("description"),
                type=ScoringCriteriaType(c["type"]),
                weight=c.get("weight"),
                min_value=c.get("min_value"),
                max_value=c.get("max_value"),
                keywords=c.get("keywords") or [],
            )
            for c in criteria
        ]

    def _get_with_criteria(self, db: Session, job_id: str):
        return (
            db.query(JobRequirement)
            .options(selectinload(JobRequirement.criteria))
            .filter(JobRequirement.id == job_id)
            .first()
        )

    def list(self) -> List[Record]:
        db = self._session()
        try:
            return (
                db.query(JobRequirement)
                .options(selectinload(JobRequirement.criteria))
                .order_by(JobRequirement.created_at.desc())
                .all()
            )
        finally:
            db.close()

    def get(self, job_id: str) -> Optional[Record]:
        db = self._session()
        try:
            return self._get_with_criteria(db, job_id)
        finally:
            db.close()

    def create(
        self, *, title: str, description: Optional[str], criteria: List[dict]
    ) -> Record:
        db = self._session()
        try:
            job = JobRequirement(title=title, description=description)
            self._build_criteria(job, criteria)
            db.add(job)
            db.commit()
            job = self._get_with_criteria(db, job.id)
            return job
        finally:
            db.close()

    def update(
        self,
        job_id: str,
        *,
        title: str,
        description: Optional[str],
        criteria: List[dict],
    ) -> Optional[Record]:
        db = self._session()
        try:
            job = db.query(JobRequirement).filter(JobRequirement.id == job_id).first()
            if not job:
                return None
            job.title = title
            job.description = description
            db.query(ScoringCriteria).filter(ScoringCriteria.job_id == job_id).delete()
            self._build_criteria(job, criteria)
            db.commit()
            job = self._get_with_criteria(db, job_id)
            return job
        finally:
            db.close()

    def delete(self, job_id: str) -> bool:
        db = self._session()
        try:
            job = db.query(JobRequirement).filter(JobRequirement.id == job_id).first()
            if not job:
                return False
            db.delete(job)
            db.commit()
            return True
        finally:
            db.close()

    def count(self) -> int:
        db = self._session()
        try:
            return db.query(JobRequirement).count()
        finally:
            db.close()


class SqlScoreRepository(ScoreRepository):
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def _session(self) -> Session:
        return self.session_factory()

    def get(self, candidate_id: str, job_id: str) -> Optional[Record]:
        db = self._session()
        try:
            return (
                db.query(Score)
                .filter(
                    Score.candidate_id == candidate_id,
                    Score.job_id == job_id,
                )
                .first()
            )
        finally:
            db.close()

    def delete(self, score_id: str) -> bool:
        db = self._session()
        try:
            score = db.query(Score).filter(Score.id == score_id).first()
            if not score:
                return False
            db.delete(score)
            db.commit()
            return True
        finally:
            db.close()

    def create(
        self,
        *,
        candidate_id: str,
        job_id: str,
        score: float,
        matched_criteria: Dict[str, float],
    ) -> Record:
        db = self._session()
        try:
            score_obj = Score(
                candidate_id=candidate_id,
                job_id=job_id,
                score=score,
                matched_criteria=matched_criteria,
            )
            db.add(score_obj)
            db.commit()
            db.refresh(score_obj)
            return score_obj
        finally:
            db.close()

    def list_by_job(self, job_id: str) -> List[Record]:
        db = self._session()
        try:
            return db.query(Score).filter(Score.job_id == job_id).all()
        finally:
            db.close()

    def set_rank(self, score_id: str, rank: int) -> None:
        db = self._session()
        try:
            score = db.query(Score).filter(Score.id == score_id).first()
            if score:
                score.rank = rank
                db.commit()
        finally:
            db.close()

    def count(self) -> int:
        db = self._session()
        try:
            return db.query(Score).count()
        finally:
            db.close()

    def all(self) -> List[Record]:
        db = self._session()
        try:
            return db.query(Score).all()
        finally:
            db.close()

    def count_higher(self, candidate_id: str, job_id: str, score: float) -> int:
        db = self._session()
        try:
            return (
                db.query(Score)
                .filter(Score.job_id == job_id, Score.score > score)
                .count()
            )
        finally:
            db.close()