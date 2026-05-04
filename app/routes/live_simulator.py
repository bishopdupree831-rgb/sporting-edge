from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.live_simulator import simulate

router = APIRouter(tags=["live-simulator"])


class LiveSimulateRequest(BaseModel):
    sport: str
    matchup: str | None = None
    market_type: str = "player_prop"
    player_name: str | None = None
    team_name: str | None = None
    stat_type: str = "Points"
    line: float = 0
    odds: int = -110
    sportsbook: str | None = None
    simulations: int = Field(10000, ge=1000, le=100000)
    live_context: dict[str, Any] = Field(default_factory=dict)


def dump_model(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@router.post("/api/live-simulate")
def live_simulate(payload: LiveSimulateRequest) -> dict[str, Any]:
    try:
        return simulate(dump_model(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
