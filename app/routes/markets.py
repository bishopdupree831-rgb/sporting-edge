from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.market_catalog import MARKET_GROUPS, SUPPORTED_SPORTBOOKS, SUPPORTED_SPORTS
from app.providers.sportsbook_provider import fetch_sportsbook_markets, provider_summary, search_sportsbook_markets

router = APIRouter(tags=["sportsbook-markets"])


@router.get("/api/markets")
def get_markets(
    sport: str = Query("NBA"),
    sportsbook: str | None = Query(None),
    event_id: str | None = Query(None),
    market_group: str | None = Query(None),
    player_name: str | None = Query(None),
    team: str | None = Query(None),
) -> dict[str, Any]:
    try:
        return fetch_sportsbook_markets(
            sport=sport,
            sportsbook=sportsbook,
            event_id=event_id,
            market_group=market_group,
            player_name=player_name,
            team=team,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        return {
            "markets": [],
            "message": str(exc),
            "provider_status": provider_summary(),
        }


@router.get("/api/markets/search")
def market_search(
    q: str = Query("", description="Search by player, team, matchup, prop type, sport, or market"),
    sport: str | None = Query(None),
    sportsbook: str | None = Query(None),
    market_group: str | None = Query(None),
    player_name: str | None = Query(None),
    team: str | None = Query(None),
) -> dict[str, Any]:
    try:
        return search_sportsbook_markets(
            q=q,
            sport=sport,
            sportsbook=sportsbook,
            market_group=market_group,
            player_name=player_name,
            team=team,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        return {
            "markets": [],
            "message": str(exc),
            "provider_status": provider_summary(),
        }


@router.get("/api/markets/catalog")
def market_catalog() -> dict[str, Any]:
    status = provider_summary()
    return {
        "sports": list(SUPPORTED_SPORTS),
        "sportsbooks": list(SUPPORTED_SPORTBOOKS),
        "market_groups": MARKET_GROUPS,
        "provider_status": status,
        "message": "Live sportsbook provider not connected." if not status["sportsbook_market_connected"] else "Live sportsbook provider connected.",
    }
