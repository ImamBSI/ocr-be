import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.db.base import (
    CandidateRepository,
    JobRepository,
    Record,
    ScoreRepository,
    UploadRepository,
    enum_value,
)
from app.db.json_store import JsonStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _criteria_record(data: dict) -> Record:
    rec = dict(data)
    rec.setdefault("id", str(uuid.uuid4()))
    rec.setdefault("created_at", _now())
    rec.setdefault("updated_at", _now())
    if rec.get("keywords") is None:
        rec["keywords"] = []
    return Record(rec)


class JsonUploadRepository(UploadRepository):
    def __init__(self, store: JsonStore):
        self.store = store

    def get(self, upload_id: str) -> Optional[Record]:
        rec = self.store.get(upload_id)
        return Record(rec) if rec else None

    def create(
        self, *, file_name: str, file_path: str, file_size: int, status
    ) -> Record:
        now = _now()
        rec = self.store.insert(
            {
                "file_name": file_name,
                "file_path": file_path,
                "file_size": file_size,
                "status": enum_value(status) or "pending",
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            }
        )
        return Record(rec)

    def delete(self, upload_id: str) -> bool:
        return self.store.delete(upload_id)

    def count(self) -> int:
        return len(self.store.all())


class JsonCandidateRepository(CandidateRepository):
    def __init__(self, store: JsonStore):
        self.store = store

    def _record(self, data: dict) -> Record:
        return Record(data)

    def get(self, candidate_id: str) -> Optional[Record]:
        rec = self.store.get(candidate_id)
        return self._record(rec) if rec else None

    def get_by_email(self, email: str) -> Optional[Record]:
        for rec in self.store.all():
            if rec.get("email") == email:
                return self._record(rec)
        return None

    def create(self, **data) -> Record:
        now = _now()
        rec = self.store.insert(
            {
                **data,
                "created_at": now,
                "updated_at": now,
            }
        )
        return self._record(rec)

    def update(self, candidate_id: str, **changes) -> Optional[Record]:
        rec = self.store.update(candidate_id, {**changes, "updated_at": _now()})
        return self._record(rec) if rec else None

    def delete(self, candidate_id: str) -> bool:
        return self.store.delete(candidate_id)

    def count(self) -> int:
        return len(self.store.all())

    def list(
        self,
        *,
        sort_by: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> Tuple[int, List[Record]]:
        records = self.store.all()
        total = len(records)

        key = sort_by if sort_by in ("name", "email", "experience_years") else "created_at"

        def sort_key(rec: dict):
            value = rec.get(key)
            return (value is None, value)

        records.sort(key=sort_key, reverse=(sort_order == "desc"))
        items = records[offset : offset + limit]
        return total, [self._record(r) for r in items]


class JsonJobRepository(JobRepository):
    def __init__(self, store: JsonStore, scores_store: JsonStore):
        self.store = store
        self.scores_store = scores_store

    def _record(self, data: dict) -> Record:
        rec = dict(data)
        if isinstance(rec.get("criteria"), list):
            rec["criteria"] = [_criteria_record(c) if isinstance(c, dict) else c for c in rec["criteria"]]
        return Record(rec)

    def list(self) -> List[Record]:
        records = self.store.all()
        records.sort(
            key=lambda r: (r.get("created_at") is None, r.get("created_at") or ""),
            reverse=True,
        )
        return [self._record(r) for r in records]

    def get(self, job_id: str) -> Optional[Record]:
        rec = self.store.get(job_id)
        return self._record(rec) if rec else None

    def create(
        self, *, title: str, description: Optional[str], criteria: List[dict]
    ) -> Record:
        now = _now()
        criteria_records = [
            _criteria_record({k: v for k, v in c.items() if v is not None})
            for c in criteria
        ]
        rec = self.store.insert(
            {
                "title": title,
                "description": description,
                "criteria": [cr.to_dict() for cr in criteria_records],
                "created_at": now,
                "updated_at": now,
            }
        )
        return self._record(rec)

    def update(
        self,
        job_id: str,
        *,
        title: str,
        description: Optional[str],
        criteria: List[dict],
    ) -> Optional[Record]:
        current = self.store.get(job_id)
        if current is None:
            return None
        criteria_records = [
            _criteria_record({k: v for k, v in c.items() if v is not None})
            for c in criteria
        ]
        rec = self.store.update(
            job_id,
            {
                "title": title,
                "description": description,
                "criteria": [cr.to_dict() for cr in criteria_records],
                "updated_at": _now(),
            },
        )
        return self._record(rec) if rec else None

    def delete(self, job_id: str) -> bool:
        score_ids = [
            r["id"]
            for r in self.scores_store.all()
            if r.get("job_id") == job_id and r.get("id")
        ]
        if score_ids:
            self.scores_store.delete_many(score_ids)
        return self.store.delete(job_id)

    def count(self) -> int:
        return len(self.store.all())


class JsonScoreRepository(ScoreRepository):
    def __init__(self, store: JsonStore):
        self.store = store

    def get(self, candidate_id: str, job_id: str) -> Optional[Record]:
        for rec in self.store.all():
            if rec.get("candidate_id") == candidate_id and rec.get("job_id") == job_id:
                return Record(rec)
        return None

    def delete(self, score_id: str) -> bool:
        return self.store.delete(score_id)

    def create(
        self,
        *,
        candidate_id: str,
        job_id: str,
        score: float,
        matched_criteria: Dict[str, float],
    ) -> Record:
        now = _now()
        rec = self.store.insert(
            {
                "candidate_id": candidate_id,
                "job_id": job_id,
                "score": score,
                "rank": None,
                "matched_criteria": matched_criteria,
                "created_at": now,
                "updated_at": now,
            }
        )
        return Record(rec)

    def list_by_job(self, job_id: str) -> List[Record]:
        return [
            Record(r) for r in self.store.all() if r.get("job_id") == job_id
        ]

    def set_rank(self, score_id: str, rank: int) -> None:
        self.store.update(score_id, {"rank": rank, "updated_at": _now()})

    def count(self) -> int:
        return len(self.store.all())

    def all(self) -> List[Record]:
        return [Record(r) for r in self.store.all()]

    def count_higher(self, candidate_id: str, job_id: str, score: float) -> int:
        return sum(
            1
            for r in self.store.all()
            if r.get("job_id") == job_id and (r.get("score") or 0) > score
        )