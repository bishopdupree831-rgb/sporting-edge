from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path(os.getenv("PROVIDER_CACHE_DIR", "/tmp/sporting-edge-cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_CACHE: dict[str, dict[str, Any]] = {}


def _path(key: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in key)
    return CACHE_DIR / f"{safe}.json"


def set_cache(key: str, data: Any, ttl: int = 60) -> None:
    record = {"saved_at": time.time(), "ttl": ttl, "data": data}
    MEMORY_CACHE[key] = record
    try:
        _path(key).write_text(json.dumps(record), encoding="utf-8")
    except OSError:
        pass


def get_cache(key: str, allow_stale: bool = False) -> Any | None:
    record = MEMORY_CACHE.get(key)
    if not record:
        try:
            record = json.loads(_path(key).read_text(encoding="utf-8"))
            MEMORY_CACHE[key] = record
        except (OSError, json.JSONDecodeError):
            record = None
    if not record:
        return None
    expired = (time.time() - float(record.get("saved_at", 0))) > int(record.get("ttl", 60))
    if expired and not allow_stale:
        return None
    return record.get("data")


def cache_meta(key: str, message: str = "Using cached data due to API limits") -> dict[str, Any]:
    record = MEMORY_CACHE.get(key)
    if not record:
        try:
            record = json.loads(_path(key).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            record = {}
    return {
        "cache_key": key,
        "cache_saved_at": record.get("saved_at"),
        "cache_message": message,
    }
