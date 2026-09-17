from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # ==================== App Config ====================
    PROJECT_NAME: str = "OCR Recruitment System"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # ==================== Database Config ====================
    # Using SQLite for development, PostgreSQL for production
    DATABASE_URL: str = Field(
        default="sqlite:///./ocr_recruitment.db",
        validation_alias="DATABASE_URL"
    )
    
    # For PostgreSQL (uncomment if using PostgreSQL)
    # DATABASE_URL: str = Field(
    #     default="postgresql://user:password@localhost/ocr_recruitment",
    #     validation_alias="DATABASE_URL"
    # )
    
    # Database configuration
    DB_POOL_SIZE: int = Field(default=20, validation_alias="DB_POOL_SIZE")
    DB_POOL_RECYCLE: int = Field(default=3600, validation_alias="DB_POOL_RECYCLE")
    DB_POOL_PRE_PING: bool = Field(default=True, validation_alias="DB_POOL_PRE_PING")
    
    # ==================== CORS Config ====================
    CORS_ORIGINS: list = [
        "http://localhost:5173",      # Frontend dev
        "http://localhost:3000",      # Alternative
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # ==================== File Upload Config ====================
    # Upload directory
    UPLOAD_DIR: str = Field(default="./uploads", validation_alias="UPLOAD_DIR")
    
    # Allowed file types
    ALLOWED_FILE_TYPES: list = ["pdf", "docx"]
    
    # Max file size (in bytes) - 10MB
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_FILE_SIZE")
    
    # ==================== OCR Config ====================
    # OCR Engine: 'tesseract' or 'azure' or 'google'
    OCR_ENGINE: str = Field(default="tesseract", validation_alias="OCR_ENGINE")
    
    # Tesseract path (needed if not in PATH)
    TESSERACT_PATH: Optional[str] = Field(default=None, validation_alias="TESSERACT_PATH")
    
    # PDF rendering DPI
    PDF_DPI: int = Field(default=300, validation_alias="PDF_DPI")
    
    # ==================== Scoring Config ====================
    # Min score threshold for ranking
    MIN_SCORE_THRESHOLD: float = Field(default=0.0, validation_alias="MIN_SCORE_THRESHOLD")
    
    # Max candidates to return in ranking
    MAX_RANKED_CANDIDATES: int = Field(default=100, validation_alias="MAX_RANKED_CANDIDATES")
    
    # ==================== API Config ====================
    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(default=20, validation_alias="DEFAULT_PAGE_SIZE")
    MAX_PAGE_SIZE: int = Field(default=100, validation_alias="MAX_PAGE_SIZE")
    
    # Request timeout (in seconds)
    REQUEST_TIMEOUT: int = Field(default=300, validation_alias="REQUEST_TIMEOUT")
    
    # ==================== Logging Config ====================
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    
    # ==================== Pydantic Config ====================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Create settings instance
settings = Settings()