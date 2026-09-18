import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.enums import UploadStatus
from app.models.upload import Upload
from app.schemas.upload import BatchUploadResponse, UploadResponse
from app.services.file_storage import delete_file, save_uploaded_file, validate_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/cv", response_model=UploadResponse)
async def upload_cv(
    file: UploadFile = File(...),
    job_requirement_id: str = None,
    db: Session = Depends(get_db),
):
    """Upload single CV file."""
    try:
        logger.info(f"Uploading CV: {file.filename}")

        validate_file(file)
        file_path = save_uploaded_file(file)
        file_size = os.path.getsize(file_path)

        upload = Upload(
            file_name=file.filename,
            file_path=file_path,
            file_size=file_size,
            status=UploadStatus.PENDING,
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        logger.info(f"Upload record created: {upload.id}")

        return UploadResponse.model_validate(upload)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.post("/cv-batch", response_model=BatchUploadResponse)
async def upload_cv_batch(
    files: list[UploadFile] = File(...),
    job_requirement_id: str = None,
    db: Session = Depends(get_db),
):
    """Upload multiple CV files dalam batch."""
    logger.info(f"Batch uploading {len(files)} files")

    results = []
    uploaded_count = 0
    failed_count = 0

    for file in files:
        try:
            validate_file(file)
            file_path = save_uploaded_file(file)
            file_size = os.path.getsize(file_path)

            upload = Upload(
                file_name=file.filename,
                file_path=file_path,
                file_size=file_size,
                status=UploadStatus.PENDING,
            )
            db.add(upload)
            db.commit()
            db.refresh(upload)

            results.append(UploadResponse.model_validate(upload))
            uploaded_count += 1

        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {str(e)}")
            failed_count += 1
            results.append(
                UploadResponse(
                    id="",
                    file_name=file.filename,
                    file_path="",
                    status=UploadStatus.FAILED,
                    message=str(e),
                )
            )

    return BatchUploadResponse(
        total=len(files),
        uploaded=uploaded_count,
        failed=failed_count,
        results=results,
    )


@router.get("/{upload_id}/status", response_model=UploadResponse)
async def get_upload_status(
    upload_id: str,
    db: Session = Depends(get_db),
):
    """Get upload status."""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    response = UploadResponse.model_validate(upload)
    response.message = upload.error_message
    return response


@router.delete("/{upload_id}")
async def delete_upload(
    upload_id: str,
    db: Session = Depends(get_db),
):
    """Delete upload dan associated file."""
    try:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()

        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        delete_file(upload.file_path)
        db.delete(upload)
        db.commit()

        return {"message": "Upload deleted successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete upload")