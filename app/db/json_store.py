import json
import os
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional


class JsonStore:
    """File JSON sederhana yang menyimpan record dalam dict keyed by id."""

    def __init__(self, path: str):
        self.path = path
        self._data: Dict[str, dict] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data = loaded if isinstance(loaded, dict) else {}
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def all(self) -> List[dict]:
        with self._lock:
            return list(self._data.values())

    def get(self, record_id: str) -> Optional[dict]:
        with self._lock:
            return self._data.get(record_id)

    def insert(self, record: dict) -> dict:
        with self._lock:
            record_id = record.get("id") or str(uuid.uuid4())
            record["id"] = record_id
            self._data[record_id] = record
            self._save()
            return record

    def update(self, record_id: str, changes: dict) -> Optional[dict]:
        with self._lock:
            record = self._data.get(record_id)
            if record is None:
                return None
            record.update(changes)
            self._save()
            return record

    def delete(self, record_id: str) -> bool:
        with self._lock:
            if record_id in self._data:
                del self._data[record_id]
                self._save()
                return True
            return False

    def delete_many(self, record_ids: List[str]) -> int:
        with self._lock:
            deleted = 0
            for record_id in record_ids:
                if record_id in self._data:
                    del self._data[record_id]
                    deleted += 1
            if deleted:
                self._save()
            return deleted

    def filter(self, predicate: Callable[[dict], bool]) -> List[dict]:
        with self._lock:
            return [r for r in self._data.values() if predicate(r)]

    def clear(self) -> None:
        with self._lock:
            self._data = {}
            self._save()