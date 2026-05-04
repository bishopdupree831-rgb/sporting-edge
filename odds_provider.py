from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests
from app.providers.cache import cache_meta, get_cache, set_cache

ODDS_BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEYS = {
    "NBA": "basketball_nba",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "MMA": "mma_mixed_martial_arts",
}
DEFAULT_MARKETS = "h2h,spreads,totals"
PLAYER_MARKETS = {
    "NBA": "player_points,player_rebounds,player_assists,player_threes",
    "NFL": "player_pass_yds,player_rush_yds,player_receptions,player_reception_yds,player_anytime_td",
    "MLB": "batter_hits,batter_total_bases,batter_home_runs,pitcher_strikeouts",
    "NHL": "player_points,player_shots_on_goal,player_saves",
}


def odds_key() -> str:
    return os.getenv("ODDS_API_KEY", "").strip()


def odds_status() -> dict:
    connected = bool(odds_key())
    return {
        "name": "odds_provider",
        "env_var": "ODDS_API_KEY",
        "connected": connected,
        "source": "The Odds API" if connected else "not connected",
        "freshness": datetime.now(timezone.utc).isoformat(),
    }


def _request(path: str, params: dict[str, Any], cache_key: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    key = odds_key()
    if not key:
        raise RuntimeError("Live provider not connected. Real-time mode unavailable.")
    final_params = {"apiKey": key, **params}
    last_error = None
    for _ in range(3):
        try:
            response = requests.get(f"{ODDS_BASE_URL}{path}", params=final_params, timeout=10)
            if response.status_code == 429:
                cached = get_cache(cache_key, allow_stale=True)
                if cached is not None:
                    return cached, {
                        "source": "The Odds API",
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                        "cache_status": "rate-limit-fallback",
                        **cache_meta(cache_key),
                    }
            response.raise_for_status()
            data = response.json()
            set_cache(cache_key, data, ttl=45)
            meta = {
                "requests_remaining": response.headers.get("x-requests-remaining"),
                "requests_used": response.headers.get("x-requests-used"),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "source": "The Odds API",
            }
            return data, meta
        except requests.RequestException as exc:
            last_error = exc
    raise RuntimeError(f"Odds provider request failed: {last_error}")


def fetch_live_odds(
    sport: str = "NBA",
    markets: str | None = None,
    regions: str = "us",
    odds_format: str = "american",
    include_player_props: bool = False,
) -> dict[str, Any]:
    sport_key = SPORT_KEYS.get(sport.upper())
    if not sport_key:
        raise ValueError("sport must be NBA, NFL, MLB, NHL, or MMA")
    requested_markets = markets or DEFAULT_MARKETS
    cache_key = f"odds:{sport_key}:{regions}:{requested_markets}:{odds_format}"
    data, meta = _request(
        f"/sports/{sport_key}/odds",
        {
            "regions": regions,
            "markets": requested_markets,
            "oddsFormat": odds_format,
            "dateFormat": "iso",
        },
        cache_key,
    )

    # The Odds API can reject player-prop markets on some plans or when mixed
    # with core markets. Keep core game markets live even if props are unavailable.
    if include_player_props and markets is None and sport.upper() in PLAYER_MARKETS:
        prop_markets = PLAYER_MARKETS[sport.upper()]
        prop_cache_key = f"odds:{sport_key}:{regions}:{prop_markets}:{odds_format}"
        try:
            prop_data, prop_meta = _request(
                f"/sports/{sport_key}/odds",
                {
                    "regions": regions,
                    "markets": prop_markets,
                    "oddsFormat": odds_format,
                    "dateFormat": "iso",
                },
                prop_cache_key,
            )
            data = [*data, *prop_data]
            meta["player_props_status"] = "loaded"
            meta["player_props_last_updated"] = prop_meta.get("last_updated")
        except RuntimeError as exc:
            meta["player_props_status"] = "unavailable"
            meta["player_props_message"] = str(exc)

    return {"events": data, "meta": meta, "provider": odds_status()}


def flatten_odds_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        matchup = f"{event.get('away_team', '')} @ {event.get('home_team', '')}".strip()
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                outcomes = market.get("outcomes", [])
                market_odds = [item.get("price") for item in outcomes if item.get("price")]
                for outcome in outcomes:
                    price = outcome.get("price")
                    if not price:
                        continue
                    rows.append({
                        "sport": event.get("sport_title"),
                        "event_id": event.get("id"),
                        "commence_time": event.get("commence_time"),
                        "matchup": matchup,
                        "market": market.get("key"),
                        "selection": outcome.get("name"),
                        "point": outcome.get("point"),
                        "sportsbook": bookmaker.get("title"),
                        "odds": int(price),
                        "market_odds": market_odds,
                        "last_update": bookmaker.get("last_update"),
                    })
    return rows
