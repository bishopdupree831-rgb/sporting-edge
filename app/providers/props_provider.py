from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

from app.providers.cache import cache_meta, get_cache, set_cache

SPORTS_GAME_ODDS_BASE = os.getenv("SPORTS_GAME_ODDS_BASE_URL", "https://api.sportsgameodds.com/v2")


def props_key() -> str:
    return (
        os.getenv("SPORTSGAMEODDS_API_KEY", "").strip()
        or os.getenv("SPORTS_GAME_ODDS_KEY", "").strip()
    )


def props_status() -> dict[str, Any]:
    connected = bool(props_key())
    return {
        "name": "props_provider",
        "env_var": "SPORTSGAMEODDS_API_KEY",
        "connected": connected,
        "source": "Sports Game Odds" if connected else "not connected",
        "freshness": datetime.now(timezone.utc).isoformat(),
    }


def fetch_props(sport: str, market: str | None = None, event_id: str | None = None) -> dict[str, Any]:
    key = props_key()
    if not key:
        raise RuntimeError("Live provider not connected. Real-time mode unavailable.")
    params = {"sport": sport.lower()}
    if market:
        params["market"] = market
    if event_id:
        params["eventID"] = event_id
    cache_key = f"sgo-props:{sport}:{market or 'all'}:{event_id or 'all'}"
    last_error = None
    for _ in range(3):
        try:
            response = requests.get(
                f"{SPORTS_GAME_ODDS_BASE}/odds",
                params=params,
                headers={"X-Api-Key": key},
                timeout=10,
            )
            if response.status_code == 429:
                cached = get_cache(cache_key, allow_stale=True)
                if cached is not None:
                    return {
                        "props": cached,
                        "meta": {
                            "source": "Sports Game Odds",
                            "last_updated": datetime.now(timezone.utc).isoformat(),
                            "cache_status": "rate-limit-fallback",
                            **cache_meta(cache_key),
                        },
                        "provider": props_status(),
                    }
            response.raise_for_status()
            data = response.json()
            set_cache(cache_key, data, ttl=45)
            return {
                "props": data,
                "meta": {"source": "Sports Game Odds", "last_updated": datetime.now(timezone.utc).isoformat()},
                "provider": props_status(),
            }
        except requests.RequestException as exc:
            last_error = exc
    cached = get_cache(cache_key, allow_stale=True)
    if cached is not None:
        return {
            "props": cached,
            "meta": {
                "source": "Sports Game Odds",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "cache_status": "request-failure-fallback",
                **cache_meta(cache_key, "Using cached data because the provider request failed"),
            },
            "provider": props_status(),
        }
    raise RuntimeError(f"Props provider request failed: {last_error}")
