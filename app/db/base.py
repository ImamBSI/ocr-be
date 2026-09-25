from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union


class Record:
    """Wrapper agar data (dari JSON ataupun SQL) bisa diakses via atribut."""

    def __init__(self, data: dict):
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value):
        if name == "_data":
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __getitem__(self, key):
        return self._data[key]

    def to_dict(self) -> dict:
        return dict(self._data)


# ==================== Repository Interfaces ====================


class UploadRepository(ABC):
    @abstractmethod
    def get(self, upload_id: str) -> Optional[Record]: ...

    @abstractmethod
    def create(
        self, *, file_name: str, file_path: str, file_size: int, status
    ) -> Record: ...

    @abstractmethod
    def delete(self, upload_id: str) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...


class CandidateRepository(ABC):
    @abstractmethod
    def get(self, candidate_id: str) -> Optional[Record]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Record]: ...

    @abstractmethod
    def create(self, **data) -> Record: ...

    @abstractmethod
    def update(self, candidate_id: str, **changes) -> Optional[Record]: ...

    @abstractmethod
    def delete(self, candidate_id: str) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def list(
        self,
        *,
        sort_by: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> Tuple[int, List[Record]]: ...


class JobRepository(ABC):
    @abstractmethod
    def list(self) -> List[Record]: ...

    @abstractmethod
    def get(self, job_id: str) -> Optional[Record]: ...

    @abstractmethod
    def create(
        self, *, title: str, description: Optional[str], criteria: List[dict]
    ) -> Record: ...

    @abstractmethod
    def update(
        self,
        job_id: str,
        *,
        title: str,
        description: Optional[str],
        criteria: List[dict],
    ) -> Optional[Record]: ...

    @abstractmethod
    def delete(self, job_id: str) -> bool: ...

    @abstractmethod
    def count(self) -> int: ...


class ScoreRepository(ABC):
    @abstractmethod
    def get(self, candidate_id: str, job_id: str) -> Optional[Record]: ...

    @abstractmethod
    def delete(self, score_id: str) -> bool: ...

    @abstractmethod
    def create(
        self,
        *,
        candidate_id: str,
        job_id: str,
        score: float,
        matched_criteria: Dict[str, float],
    ) -> Record: ...

    @abstractmethod
    def list_by_job(self, job_id: str) -> List[Record]: ...

    @abstractmethod
    def set_rank(self, score_id: str, rank: int) -> None: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def all(self) -> List[Record]: ...

    @abstractmethod
    def count_higher(self, candidate_id: str, job_id: str, score: float) -> int: ...


@dataclass
class Repositories:
    uploads: UploadRepository
    candidates: CandidateRepository
    jobs: JobRepository
    scores: ScoreRepository


# ==================== Enum Helpers ====================


def enum_value(value: Union[str, object, None]) -> Optional[str]:
    """Konversi Enum/str menjadi string value untuk penyimpanan JSON."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)