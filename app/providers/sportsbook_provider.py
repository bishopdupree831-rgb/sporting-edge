from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from app.market_catalog import (
    MARKET_GROUPS,
    SUPPORTED_SPORTBOOKS,
    UNCONNECTED_MESSAGE,
    clean_book,
    clean_sport,
    filter_markets,
    normalize_odds_api_events,
    search_markets,
)
from app.providers.draftkings_provider import affiliate_link as dk_link
from app.providers.fanduel_provider import affiliate_link as fd_link
from app.providers.odds_provider import fetch_live_odds, odds_status
from app.providers.props_provider import props_status


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def approved_transfer_connected() -> bool:
    return bool(os.getenv("SHARPSPORTS_API_KEY", "").strip())


def sportsbook_links() -> dict[str, str | None]:
    return {"DraftKings": dk_link(), "FanDuel": fd_link()}


def optional_provider_statuses() -> list[dict[str, Any]]:
    providers = [
        ("sportsdata_provider", "SPORTSDATA_API_KEY", "SportsDataIO"),
        ("opticodds_provider", "OPTICODDS_API_KEY", "OpticOdds"),
        ("sharpsports_provider", "SHARPSPORTS_API_KEY", "SharpSports"),
    ]
    return [
        {
            "name": name,
            "env_var": env_var,
            "connected": bool(os.getenv(env_var, "").strip()),
            "source": source if os.getenv(env_var, "").strip() else "not connected",
            "freshness": now_iso(),
        }
        for name, env_var, source in providers
    ]


def provider_summary() -> dict[str, Any]:
    odds = odds_status()
    props = props_status()
    optional = optional_provider_statuses()
    return {
        "connected": bool(odds.get("connected") or props.get("connected") or any(item["connected"] for item in optional)),
        "sportsbook_market_connected": bool(odds.get("connected") or props.get("connected")),
        "sources": [odds, props, *optional],
        "sportsbooks": list(SUPPORTED_SPORTBOOKS),
        "affiliate_links": sportsbook_links(),
        "direct_transfer_connected": approved_transfer_connected(),
        "last_updated": now_iso(),
    }


def fetch_sportsbook_markets(
    *,
    sport: str,
    sportsbook: str | None = None,
    event_id: str | None = None,
    market_group: str | None = None,
    player_name: str | None = None,
    team: str | None = None,
) -> dict[str, Any]:
    sport_value = clean_sport(sport)
    book_value = clean_book(sportsbook)
    sources = [odds_status(), props_status()]
    if not odds_status().get("connected"):
        return {
            "markets": [],
            "message": UNCONNECTED_MESSAGE,
            "data_freshness": now_iso(),
            "provider_sources": sources,
            "supported_market_groups": MARKET_GROUPS.get(sport_value, []),
            "sportsbook_links": sportsbook_links(),
        }

    live = fetch_live_odds(sport=sport_value, include_player_props=True)
    markets = normalize_odds_api_events(live.get("events", []), sport=sport_value, sportsbook=book_value)
    markets = filter_markets(
        markets,
        sport=sport_value,
        sportsbook=book_value,
        event_id=event_id,
        market_group=market_group,
        player_name=player_name,
        team=team,
    )
    meta = live.get("meta", {})
    return {
        "markets": markets,
        "message": "Live sportsbook markets loaded.",
        "data_freshness": meta.get("last_updated") or now_iso(),
        "provider_sources": [live.get("provider") or odds_status(), props_status()],
        "supported_market_groups": MARKET_GROUPS.get(sport_value, []),
        "sportsbook_links": sportsbook_links(),
    }


def search_sportsbook_markets(
    *,
    q: str,
    sport: str | None = None,
    sportsbook: str | None = None,
    market_group: str | None = None,
    player_name: str | None = None,
    team: str | None = None,
) -> dict[str, Any]:
    sports = [clean_sport(sport)] if sport else ["NBA", "NFL", "MLB", "NHL", "MMA"]
    all_markets: list[dict[str, Any]] = []
    latest = now_iso()
    provider_sources: list[dict[str, Any]] = [odds_status(), props_status()]
    if not odds_status().get("connected"):
        return {
            "markets": [],
            "message": UNCONNECTED_MESSAGE,
            "data_freshness": latest,
            "provider_sources": provider_sources,
            "sportsbook_links": sportsbook_links(),
        }
    for sport_value in sports:
        fetched = fetch_sportsbook_markets(
            sport=sport_value,
            sportsbook=sportsbook,
            market_group=market_group,
            player_name=player_name,
            team=team,
        )
        all_markets.extend(fetched.get("markets", []))
        latest = fetched.get("data_freshness") or latest
        provider_sources = fetched.get("provider_sources") or provider_sources
    return {
        "markets": search_markets(all_markets, q, sport=sport, sportsbook=sportsbook),
        "message": "Live sportsbook market search complete.",
        "data_freshness": latest,
        "provider_sources": provider_sources,
        "sportsbook_links": sportsbook_links(),
    }
