from __future__ import annotations

from app.providers.injury_provider import injury_status
from app.providers.news_provider import news_status
from app.providers.odds_provider import odds_status
from app.providers.props_provider import props_status
from app.providers.stats_provider import stats_status


def provider_statuses() -> list[dict]:
    return [odds_status(), stats_status(), props_status(), injury_status(), news_status()]


def live_provider_connected() -> bool:
    return any(source["connected"] for source in provider_statuses())
