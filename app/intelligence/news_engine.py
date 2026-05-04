from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


DEFAULT_NEWS = [
    {
        "sport": "NBA",
        "headline": "Lineup verification: monitor late scratches and minute limits before lock.",
        "impact": "injury",
        "severity": 72,
    },
    {
        "sport": "NFL",
        "headline": "Weather and playing surface should be checked for passing, kicking, and explosive-play props.",
        "impact": "environment",
        "severity": 65,
    },
    {
        "sport": "NHL",
        "headline": "Goalie confirmation and back-to-back fatigue can swing totals and save props.",
        "impact": "lineup",
        "severity": 69,
    },
    {
        "sport": "MLB",
        "headline": "Park factor, bullpen fatigue, and handedness splits remain core prop inputs.",
        "impact": "matchup",
        "severity": 67,
    },
]


def player_news(sport: str | None = None, team: str | None = None) -> dict[str, Any]:
    selected = [item for item in DEFAULT_NEWS if not sport or item["sport"] == sport.upper()]
    if not selected:
        selected = DEFAULT_NEWS
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "team_filter": team or "all",
        "items": selected,
        "source": "provider-ready news engine",
        "note": "Connect a news API key for real injury-wire headlines; these rules stay active as fallback.",
    }
