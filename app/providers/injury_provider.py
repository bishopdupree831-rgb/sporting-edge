from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from app.providers.stats_provider import fetch_api_sports


def injury_status() -> dict:
    connected = bool(os.getenv("API_SPORTS_KEY") or os.getenv("RAPIDAPI_KEY"))
    return {
        "name": "injury_provider",
        "env_var": "API_SPORTS_KEY",
        "connected": connected,
        "source": "API-Sports injuries/status" if connected else "not connected",
        "freshness": datetime.now(timezone.utc).isoformat(),
    }


def fetch_injuries(sport: str) -> dict[str, Any]:
    endpoint = {
        "NFL": "injuries",
        "NBA": "injuries",
        "MLB": "injuries",
        "NHL": "injuries",
        "MMA": "fighters",
    }.get(sport.upper(), "injuries")
    return fetch_api_sports(sport, endpoint, ttl=60)
