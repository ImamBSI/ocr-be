import logging
from typing import Optional

from app.services.ai.base import AIProvider, ParsedCV
from app.services.ocr import CVParsingService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a CV parser. Extract structured data from the CV text below and return a single JSON object with exactly these keys:
- name (string): person's full name. Use "Unknown" only if truly not present.
- email (string or null): email address if present.
- phone (string or null): phone number if present.
- experience_years (integer or null): total professional work experience in years; 0 if not found.
- education (string or null): highest relevant degree/institution line.
- skills (array of strings): technical/professional skills, normalized, deduplicated, lowercase.
- summary (string or null): one concise sentence summarizing the candidate.
Return valid JSON only, no markdown."""


def _build_user_prompt(text: str) -> str:
    return f"Extract structured data from this CV:\n\n{text[:4500]}"


async def extract_cv(provider: AIProvider, text: str) -> Optional[ParsedCV]:
    """
    Parse CV menggunakan LLM.

    Returns:
        ParsedCV jika sukses, None jika gagal (caller bisa fallback rule-based).
    """
    try:
        result = await provider.complete_json(
            system=_SYSTEM_PROMPT,
            user=_build_user_prompt(text),
            schema=ParsedCV,
        )

        # Sanitasi output
        if not result.name or result.name.strip().lower() in (
            "unknown",
            "not found",
            "n/a",
        ):
            result.name = "Unknown"

        result.skills = list(
            dict.fromkeys(
                [s.strip().lower() for s in (result.skills or []) if s.strip()]
            )
        )

        if result.experience_years is not None:
            try:
                years = int(result.experience_years)
                result.experience_years = max(0, min(70, years))
            except (TypeError, ValueError):
                result.experience_years = 0

        return result
    except Exception as exc:
        logger.warning("AI CV extraction failed, will fallback: %s", exc)
        return None


def fallback_parse(text: str) -> ParsedCV:
    """Fallback ke parser rule-based yang sudah ada."""
    data = CVParsingService.parse_cv(text)
    return ParsedCV(
        name=data.get("name", "Unknown"),
        email=data.get("email") or None,
        phone=data.get("phone") or None,
        experience_years=int(data.get("experience_years", 0) or 0),
        education=data.get("education") or None,
        skills=data.get("skills", []),
        summary=None,
    )
