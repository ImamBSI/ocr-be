from app.db.base import Repositories
from app.db.factory import repositories
from app.db.session import get_db


def get_repos() -> Repositories:
    return repositories


__all__ = ["get_db", "get_repos", "Repositories"]