import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from config import settings
from database.connection import get_db
from models.models import Upload, UploadStatus
from schemas.schemas import UploadResponse, BatchUploadResponse
from services.ocr import CVProcessingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])


# ==================== Helper Functions ====================
def save_uploaded_file(file: UploadFile) -> str:
    """
    Save uploaded file ke disk
    
    Args:
        file: UploadFile object
        
    Returns:
        File path
    """
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    import uuid
    file_id = str(uuid.uuid4())
    file_ext = file.filename.split('.')[-1]
    filename = f"{file_id}.{file_ext}"
    
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    logger.info(f"File saved: {file_path}")
    return file_path


def validate_file(file: UploadFile) -> None:
    """
    Validate uploaded file
    
    Args:
        file: UploadFile object
        
    Raises:
        HTTPException if validation fails
    """
    # Check file size
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
        )
    
    file.file.seek(0)  # Reset file pointer
    
    # Check file type
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )


# ==================== Routes ====================
@router.post("/cv", response_model=UploadResponse)
async def upload_cv(
    file: UploadFile = File(...),
    job_requirement_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Upload single CV file
    
    Returns:
        Upload response with file info
    """
    try:
        logger.info(f"Uploading CV: {file.filename}")
        
        # Validate file
        validate_file(file)
        
        # Save file
        file_path = save_uploaded_file(file)
        file_size = os.path.getsize(file_path)
        
        # Create upload record
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
        
        return UploadResponse(
            id=upload.id,
            file_name=upload.file_name,
            file_path=upload.file_path,
            file_size=upload.file_size,
            status=upload.status,
            created_at=upload.created_at,
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.post("/cv-batch", response_model=BatchUploadResponse)
async def upload_cv_batch(
    files: list[UploadFile] = File(...),
    job_requirement_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Upload multiple CV files in batch
    
    Returns:
        Batch upload response with results
    """
    logger.info(f"Batch uploading {len(files)} files")
    
    results = []
    uploaded_count = 0
    failed_count = 0
    
    for file in files:
        try:
            # Validate file
            validate_file(file)
            
            # Save file
            file_path = save_uploaded_file(file)
            file_size = os.path.getsize(file_path)
            
            # Create upload record
            upload = Upload(
                file_name=file.filename,
                file_path=file_path,
                file_size=file_size,
                status=UploadStatus.PENDING,
            )
            
            db.add(upload)
            db.commit()
            db.refresh(upload)
            
            results.append(UploadResponse(
                id=upload.id,
                file_name=upload.file_name,
                file_path=upload.file_path,
                file_size=upload.file_size,
                status=upload.status,
                created_at=upload.created_at,
            ))
            
            uploaded_count += 1
            
        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {str(e)}")
            failed_count += 1
            results.append(UploadResponse(
                id="",
                file_name=file.filename,
                file_path="",
                status=UploadStatus.FAILED,
                message=str(e),
            ))
    
    return BatchUploadResponse(
        total=len(files),
        uploaded=uploaded_count,
        failed=failed_count,
        results=results,
    )


@router.get("/{upload_id}/status", response_model=UploadResponse)
async def get_upload_status(
    upload_id: str,
    db: Session = Depends(get_db)
):
    """
    Get upload status
    
    Returns:
        Upload response with current status
    """
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return UploadResponse(
        id=upload.id,
        file_name=upload.file_name,
        file_path=upload.file_path,
        file_size=upload.file_size,
        status=upload.status,
        message=upload.error_message,
        created_at=upload.created_at,
    )


@router.delete("/{upload_id}")
async def delete_upload(
    upload_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete upload dan associated file
    """
    try:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Delete file from disk
        if os.path.exists(upload.file_path):
            os.remove(upload.file_path)
            logger.info(f"File deleted: {upload.file_path}")
        
        # Delete upload record
        db.delete(upload)
        db.commit()
        
        return {"message": "Upload deleted successfully"}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete upload")