import logging
from typing import Dict, List, Optional

from app.db.base import Record
from app.services.ai.base import AIProvider, CriteriaScoresResponse

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert recruiter. Evaluate a candidate against each job criterion.
Return a single JSON object with one key "criteria", whose value is an array of objects.
Each object must have exactly these keys:
- name (string): the exact criterion name from the input.
- score (integer 0-100): 100 if clearly meets/exceeds, 0 if no evidence.
- evidence (string or null): a short quote from the CV (max 120 chars) supporting the score.
- confidence (float 0.0-1.0): how clear the evidence is.
Be strict and objective. Return valid JSON only, no markdown."""


def _build_user_prompt(candidate: Record, job: Record) -> str:
    lines = ["=== CV TEXT ===", candidate.cv_text or "(no text)"]
    lines.append("\n=== JOB CRITERIA ===")

    for criterion in job.criteria:
        ctype = getattr(criterion, "type", "custom")
        weight = getattr(criterion, "weight", 1.0)
        keywords = getattr(criterion, "keywords", None) or []
        min_value = getattr(criterion, "min_value", None)
        max_value = getattr(criterion, "max_value", None)
        description = getattr(criterion, "description", None) or ""

        detail_parts = [f"type={ctype}", f"weight={weight}"]
        if keywords:
            detail_parts.append(f"keywords={', '.join(keywords)}")
        if min_value is not None or max_value is not None:
            detail_parts.append(
                f"range={min_value or 0}-{max_value or 'unlimited'}"
            )
        lines.append(
            f"- {criterion.name} ({', '.join(detail_parts)}). {description}".strip()
        )

    return "\n".join(lines)[:6000]


async def score_criteria(
    provider: AIProvider, candidate: Record, job: Record
) -> Optional[Dict[str, object]]:
    """
    Skor candidate dengan rubrik LLM per kriteria.

    Returns:
        Mapping nama_kriteria -> CriteriaScore, atau None jika gagal.
    """
    try:
        result = await provider.complete_json(
            system=_SYSTEM_PROMPT,
            user=_build_user_prompt(candidate, job),
            schema=CriteriaScoresResponse,
        )
        return {cs.name: cs for cs in result.criteria}
    except Exception as exc:
        logger.warning("AI scoring failed, will fallback: %s", exc)
        return None
