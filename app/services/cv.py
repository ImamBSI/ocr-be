import logging

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.upload import Upload
from app.services.file_storage import get_file_type
from app.services.ocr import CVProcessingService

logger = logging.getLogger(__name__)


class CVService:
    """Service untuk processing dan persistence data candidate."""

    @staticmethod
    def process_upload(db: Session, upload: Upload) -> Candidate:
        """
        Process CV dari upload record: extract text, parse, lalu upsert candidate.

        Args:
            db: Database session
            upload: Upload record yang berisi file CV

        Returns:
            Candidate object (baru atau yang di-update)
        """
        if not upload.file_path:
            raise ValueError("File path not found")

        file_type = get_file_type(upload.file_path)
        parsed_data = CVProcessingService.process_cv_file(
            upload.file_path, file_type
        )

        candidate = db.query(Candidate).filter(
            Candidate.email == parsed_data.get("email")
        ).first()

        if candidate:
            candidate.name = parsed_data.get("name", candidate.name)
            candidate.phone = parsed_data.get("phone", candidate.phone)
            candidate.experience_years = parsed_data.get("experience_years", 0)
            candidate.skills = parsed_data.get("skills", [])
            candidate.education = parsed_data.get("education")
            candidate.cv_text = parsed_data.get("cv_text")
            candidate.file_name = upload.file_name
            candidate.file_path = upload.file_path
            candidate.is_processed = 1
            logger.info(f"Updated existing candidate: {candidate.id}")
        else:
            candidate = Candidate(
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
            db.add(candidate)
            logger.info(f"Created new candidate: {candidate.id}")

        db.commit()
        db.refresh(candidate)

        return candidate