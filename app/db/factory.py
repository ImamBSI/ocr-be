import json
import os

from app.core.config import settings
from app.db.base import Repositories
from app.db.json_repo import (
    JsonCandidateRepository,
    JsonJobRepository,
    JsonScoreRepository,
    JsonUploadRepository,
)
from app.db.json_store import JsonStore
from app.db.sql_repo import (
    SqlCandidateRepository,
    SqlJobRepository,
    SqlScoreRepository,
    SqlUploadRepository,
)

APP_DB_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILES = {
    "uploads": os.path.join(APP_DB_DIR, "uploads.json"),
    "candidates": os.path.join(APP_DB_DIR, "candidates.json"),
    "jobs": os.path.join(APP_DB_DIR, "jobs.json"),
    "scores": os.path.join(APP_DB_DIR, "scores.json"),
}


def _build_json_repositories() -> Repositories:
    stores = {name: JsonStore(path) for name, path in JSON_FILES.items()}
    return Repositories(
        uploads=JsonUploadRepository(stores["uploads"]),
        candidates=JsonCandidateRepository(stores["candidates"]),
        jobs=JsonJobRepository(stores["jobs"], stores["scores"]),
        scores=JsonScoreRepository(stores["scores"]),
    )


def _build_sql_repositories() -> Repositories:
    from app.db.session import SessionLocal

    return Repositories(
        uploads=SqlUploadRepository(SessionLocal),
        candidates=SqlCandidateRepository(SessionLocal),
        jobs=SqlJobRepository(SessionLocal),
        scores=SqlScoreRepository(SessionLocal),
    )


def get_repositories() -> Repositories:
    backend = settings.STORAGE_BACKEND.strip().lower()
    if backend == "sql":
        return _build_sql_repositories()
    return _build_json_repositories()


def init_storage() -> None:
    """Siapkan storage (buat folder & file JSON kosong, atau init DB SQL)."""
    backend = settings.STORAGE_BACKEND.strip().lower()
    if backend == "sql":
        from app.db.session import init_db

        init_db()
        return

    os.makedirs(APP_DB_DIR, exist_ok=True)
    for name, path in JSON_FILES.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f)


def check_storage() -> bool:
    backend = settings.STORAGE_BACKEND.strip().lower()
    if backend == "sql":
        from app.db.session import check_db_connection

        return check_db_connection()
    return True


# Singleton yang dipakai semua route (FastAPI dependency)
repositories = get_repositories()