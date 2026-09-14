from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Config
    PROJECT_NAME: str = "FastAPI Template"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Multi-Database Config (Menggunakan Field Alias)
    db_postgres_1: str = Field(..., validation_alias="DB_POSTGRES_1_URL")
    db_postgres_2: str = Field(..., validation_alias="DB_POSTGRES_2_URL")
    db_mysql_1: str = Field(..., validation_alias="DB_MYSQL_1_URL")
    db_mongo_1: str = Field(..., validation_alias="DB_MONGO_1_URL")

    # Mengatur Pydantic agar membaca file .env secara otomatis
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Mengabaikan variabel ekstra di .env agar tidak error
    )

# Inisialisasi settings yang bisa dipanggil di file lain
settings = Settings()