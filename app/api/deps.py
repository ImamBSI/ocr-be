import secrets
from typing import Optional

from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.db.base import Repositories
from app.db.factory import repositories
from app.db.session import get_db

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_repos() -> Repositories:
    return repositories


def verify_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
) -> None:
    """
    Verifikasi API key pada header `X-API-Key`.

    Jika settings.API_KEY kosong, autentikasi dinonaktifkan (mode pengembangan).
    """
    expected = settings.API_KEY
    if not expected:
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )


__all__ = ["get_db", "get_repos", "verify_api_key", "Repositories"]
