import logging
import os
import shutil
import uuid

from fastapi import HTTPException, UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)


def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file ke disk dan kembalikan file path."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_ext = file.filename.split(".")[-1]
    filename = f"{file_id}.{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"File saved: {file_path}")
    return file_path


def validate_file(file: UploadFile) -> None:
    """Validasi ukuran dan tipe file upload."""
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                "File too large. Max size: "
                f"{settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
            ),
        )

    file.file.seek(0)

    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "File type not allowed. Allowed types: "
                f"{', '.join(settings.ALLOWED_FILE_TYPES)}"
            ),
        )


def delete_file(file_path: str) -> None:
    """Hapus file dari disk jika ada."""
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"File deleted: {file_path}")


def get_file_type(file_path: str) -> str:
    """Ekstrak tipe file dari path."""
    return file_path.split(".")[-1].lower()