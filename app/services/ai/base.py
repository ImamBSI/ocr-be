from abc import ABC, abstractmethod
from typing import Optional, Type
from pydantic import BaseModel, Field

class ParsedCV(BaseModel):
    name: str = Field(..., min_length=1)
    email: Optional[str] = None
    phone: Optional[str] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    summary: Optional[str] = None


class CriteriaScore(BaseModel):
    name: str
    score: float = Field(..., ge=0, le=100)
    evidence: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0, le=1)


class CriteriaScoresResponse(BaseModel):
    criteria: list[CriteriaScore]


class AIProvider(ABC):
    @abstractmethod
    async def complete_json(
        self, system: str, user: str, schema: Type[BaseModel]
    ) -> BaseModel:
        """
        Kirim prompt ke LLM dan kembalikan instance schema yang sudah tervalidasi.

        Raises:
            AIError: jika request/parse/validasi gagal setelah retry.
        """
        ...


class AIError(Exception):
    pass
