from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==================== App Config ====================
    PROJECT_NAME: str = "OCR Recruitment System"
    DEBUG: bool = True
    API_STR: str = "/api/"

    # ==================== Database Config ====================
    DATABASE_URL: str = Field(
        default="sqlite:///./ocr_recruitment.db",
        validation_alias="DATABASE_URL",
    )
    DB_POOL_SIZE: int = Field(default=20, validation_alias="DB_POOL_SIZE")
    DB_POOL_RECYCLE: int = Field(default=3600, validation_alias="DB_POOL_RECYCLE")
    DB_POOL_PRE_PING: bool = Field(default=True, validation_alias="DB_POOL_PRE_PING")

    # ==================== CORS Config ====================
    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    # ==================== File Upload Config ====================
    UPLOAD_DIR: str = Field(default="./uploads", validation_alias="UPLOAD_DIR")
    ALLOWED_FILE_TYPES: list = ["pdf", "docx"]
    MAX_FILE_SIZE: int = Field(
        default=10 * 1024 * 1024, validation_alias="MAX_FILE_SIZE"
    )

    # ==================== OCR Config ====================
    OCR_ENGINE: str = Field(default="tesseract", validation_alias="OCR_ENGINE")
    TESSERACT_PATH: Optional[str] = Field(
        default=None, validation_alias="TESSERACT_PATH"
    )
    PDF_DPI: int = Field(default=300, validation_alias="PDF_DPI")

    # ==================== Scoring Config ====================
    MIN_SCORE_THRESHOLD: float = Field(
        default=0.0, validation_alias="MIN_SCORE_THRESHOLD"
    )
    MAX_RANKED_CANDIDATES: int = Field(
        default=100, validation_alias="MAX_RANKED_CANDIDATES"
    )

    # ==================== API Config ====================
    DEFAULT_PAGE_SIZE: int = Field(
        default=20, validation_alias="DEFAULT_PAGE_SIZE"
    )
    MAX_PAGE_SIZE: int = Field(default=100, validation_alias="MAX_PAGE_SIZE")
    REQUEST_TIMEOUT: int = Field(
        default=300, validation_alias="REQUEST_TIMEOUT"
    )

    # ==================== Logging Config ====================
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()