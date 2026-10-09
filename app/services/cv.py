import logging

from app.db.base import Record, Repositories
from app.services.ai.extract import extract_cv, fallback_parse
from app.services.ai.factory import get_ai_provider
from app.services.file_storage import get_file_type
from app.services.ocr import OCRService

logger = logging.getLogger(__name__)


class CVService:
    @staticmethod
    async def process_upload(repos: Repositories, upload: Record) -> Record:
        """
        Process CV dari upload record: extract text, parse (LLM/rule), lalu upsert candidate.

        Args:
            repos: Kumpulan repository storage
            upload: Upload record yang berisi file CV

        Returns:
            Candidate record (baru atau yang di-update)
        """
        if not upload.file_path:
            raise ValueError("File path not found")

        file_type = get_file_type(upload.file_path)
        text = OCRService.extract_text(upload.file_path, file_type)
        logger.info(f"Extracted {len(text)} characters from CV")

        provider = get_ai_provider()
        if provider:
            parsed = await extract_cv(provider, text)
            if parsed is None:
                parsed = fallback_parse(text)
                parsed_by = "rule"
            else:
                parsed_by = "llm"
        else:
            parsed = fallback_parse(text)
            parsed_by = "rule"

        candidate = repos.candidates.get_by_email(parsed.email or "")

        common_data = {
            "name": parsed.name,
            "phone": parsed.phone,
            "experience_years": parsed.experience_years or 0,
            "skills": parsed.skills,
            "education": parsed.education,
            "cv_text": text[:5000],
            "summary": parsed.summary,
            "parsed_by": parsed_by,
        }

        if candidate:
            candidate = repos.candidates.update(candidate.id, **common_data)
            logger.info(f"Updated existing candidate: {candidate.id}")
        else:
            candidate = repos.candidates.create(
                **common_data,
                upload_id=upload.id,
                email=parsed.email or "",
                file_name=upload.file_name,
                file_path=upload.file_path,
                is_processed=1,
            )
            logger.info(f"Created new candidate: {candidate.id}")

        return candidate
