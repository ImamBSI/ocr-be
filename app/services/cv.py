import logging

from app.db.base import Record, Repositories
from app.services.file_storage import get_file_type
from app.services.ocr import CVProcessingService

logger = logging.getLogger(__name__)


class CVService:
    """Service untuk processing dan persistence data candidate."""

    @staticmethod
    def process_upload(repos: Repositories, upload: Record) -> Record:
        """
        Process CV dari upload record: extract text, parse, lalu upsert candidate.

        Args:
            repos: Kumpulan repository storage
            upload: Upload record yang berisi file CV

        Returns:
            Candidate record (baru atau yang di-update)
        """
        if not upload.file_path:
            raise ValueError("File path not found")

        file_type = get_file_type(upload.file_path)
        parsed_data = CVProcessingService.process_cv_file(
            upload.file_path, file_type
        )

        candidate = repos.candidates.get_by_email(parsed_data.get("email"))

        if candidate:
            candidate = repos.candidates.update(
                candidate.id,
                name=parsed_data.get("name", candidate.name),
                phone=parsed_data.get("phone", candidate.phone),
                experience_years=parsed_data.get("experience_years", 0),
                skills=parsed_data.get("skills", []),
                education=parsed_data.get("education"),
                cv_text=parsed_data.get("cv_text"),
                file_name=upload.file_name,
                file_path=upload.file_path,
                is_processed=1,
            )
            logger.info(f"Updated existing candidate: {candidate.id}")
        else:
            candidate = repos.candidates.create(
                upload_id=upload.id,
                name=parsed_data.get("name", "Unknown"),
                email=parsed_data.get("email", ""),
                phone=parsed_data.get("phone"),
                experience_years=parsed_data.get("experience_years", 0),
                skills=parsed_data.get("skills", []),
                education=parsed_data.get("education"),
                cv_text=parsed_data.get("cv_text"),
                file_name=upload.file_name,
                file_path=upload.file_path,
                is_processed=1,
            )
            logger.info(f"Created new candidate: {candidate.id}")

        return candidate