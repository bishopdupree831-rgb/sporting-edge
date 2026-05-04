from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.intelligence.news_engine import player_news
from app.intelligence.projection_engine import daily_card, project_prop, trend_card
from app.intelligence.query_engine import answer_query

router = APIRouter()


class QueryPayload(BaseModel):
    query: str


class ProjectionPayload(BaseModel):
    sport: str = "NBA"
    player: str = "Selected player"
    market: str = "Points"
    line: float = 24.5
    odds: int = -110
    recent: list[float] | None = None
    team: str | None = None
    opponent: str | None = None
    venue: str | None = None
    status: str | None = None


def dump_model(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@router.post("/api/query")
def query(payload: QueryPayload) -> dict[str, Any]:
    return answer_query(payload.query)


@router.get("/api/player-news")
def news(sport: str | None = None, team: str | None = None) -> dict[str, Any]:
    return player_news(sport, team)


@router.post("/api/projection")
def projection(payload: ProjectionPayload) -> dict[str, Any]:
    return project_prop(dump_model(payload))


@router.post("/api/trend-card")
def trend(payload: ProjectionPayload) -> dict[str, Any]:
    return trend_card(dump_model(payload))


@router.post("/api/daily-card")
def daily(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    sport = (payload or {}).get("sport", "NBA")
    return daily_card(str(sport))
