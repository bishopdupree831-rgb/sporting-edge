from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests
from app.providers.cache import cache_meta, get_cache, set_cache

API_SPORTS_HOSTS = {
    "NBA": "v1.basketball.api-sports.io",
    "NFL": "v1.american-football.api-sports.io",
    "MLB": "v1.baseball.api-sports.io",
    "NHL": "v1.hockey.api-sports.io",
    "MMA": "v1.mma.api-sports.io",
}


def api_sports_key() -> str:
    return os.getenv("API_SPORTS_KEY", "").strip() or os.getenv("RAPIDAPI_KEY", "").strip()


def stats_status() -> dict:
    connected = bool(api_sports_key())
    return {
        "name": "stats_provider",
        "env_var": "API_SPORTS_KEY",
        "connected": connected,
        "source": "API-Sports" if connected else "not connected",
        "freshness": datetime.now(timezone.utc).isoformat(),
    }


def fetch_api_sports(sport: str, endpoint: str, params: dict[str, Any] | None = None, ttl: int = 60) -> dict[str, Any]:
    key = api_sports_key()
    host = API_SPORTS_HOSTS.get(sport.upper())
    if not key:
        raise RuntimeError("Live provider not connected. Real-time mode unavailable.")
    if not host:
        raise ValueError("sport must be NBA, NFL, MLB, NHL, or MMA")
    clean_endpoint = endpoint.strip("/")
    query = params or {}
    cache_key = f"api-sports:{sport.upper()}:{clean_endpoint}:{jsonable_key(query)}"
    last_error = None
    for _ in range(3):
        try:
            response = requests.get(
                f"https://{host}/{clean_endpoint}",
                params=query,
                headers={"x-apisports-key": key},
                timeout=10,
            )
            if response.status_code == 429:
                cached = get_cache(cache_key, allow_stale=True)
                if cached is not None:
                    return {
                        "data": cached,
                        "meta": {
                            "source": "API-Sports",
                            "last_updated": datetime.now(timezone.utc).isoformat(),
                            "endpoint": clean_endpoint,
                            "cache_status": "rate-limit-fallback",
                            **cache_meta(cache_key),
                        },
                        "provider": stats_status(),
                    }
            response.raise_for_status()
            data = response.json()
            set_cache(cache_key, data, ttl=ttl)
            return {
                "data": data,
                "meta": {
                    "source": "API-Sports",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "endpoint": clean_endpoint,
                },
                "provider": stats_status(),
            }
        except requests.RequestException as exc:
            last_error = exc
    cached = get_cache(cache_key, allow_stale=True)
    if cached is not None:
        return {
            "data": cached,
            "meta": {
                "source": "API-Sports",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "endpoint": clean_endpoint,
                "cache_status": "request-failure-fallback",
                **cache_meta(cache_key, "Using cached data because the provider request failed"),
            },
            "provider": stats_status(),
        }
    raise RuntimeError(f"Stats provider request failed: {last_error}")


def jsonable_key(params: dict[str, Any]) -> str:
    return "&".join(f"{key}={params[key]}" for key in sorted(params))


def fetch_live_games(sport: str, **params: Any) -> dict[str, Any]:
    return fetch_api_sports(sport, "games", params, ttl=45)


def fetch_team_stats(sport: str, **params: Any) -> dict[str, Any]:
    endpoint = "standings" if sport.upper() in {"NBA", "NFL", "MLB", "NHL"} else "fighters"
    return fetch_api_sports(sport, endpoint, params, ttl=300)


def fetch_player_stats(sport: str, **params: Any) -> dict[str, Any]:
    endpoint = "players" if sport.upper() != "MMA" else "fighters"
    return fetch_api_sports(sport, endpoint, params, ttl=300)
