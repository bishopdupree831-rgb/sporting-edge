from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.alerts import create_alert, list_alerts
from app.arbitrage_engine import find_arbitrage
from app.bankroll import bankroll_sizing
from app.clv_tracker import log_bet, performance
from app.line_movement import track_line_movement
from app.model_builder import simulate_model
from app.value_engine import positive_ev_feed

router = APIRouter(tags=["sharp-terminal"])


class ArbitrageRequest(BaseModel):
    outcomes: list[dict[str, Any]]
    bankroll: float = 1000


class LineMovementRequest(BaseModel):
    opening_line: float
    current_line: float
    line_history: list[float] | None = None
    public_betting_percentage: float = 50
    public_money_percentage: float = 50
    steam_threshold: float = 1


class BetLogRequest(BaseModel):
    sport: str = "Unknown"
    bet: str = "Manual bet"
    market: str = "Unknown"
    sportsbook: str = "manual"
    odds_taken: int
    closing_odds: int | None = None
    line_taken: float | None = None
    closing_line: float | None = None
    units: float = Field(1, gt=0)
    outcome: str = "pending"


class BankrollRequest(BaseModel):
    bankroll: float = Field(..., gt=0)
    odds: int
    model_probability: float = Field(..., gt=0, lt=1)
    risk_level: str = "medium"


class AlertRequest(BaseModel):
    type: str = "value_bet"
    target: str = "manual target"
    condition: str = "notify when triggered"
    threshold: float | None = None
    active: bool = True


class ModelBuilderRequest(BaseModel):
    odds: int = -110
    weights: dict[str, float] | None = None
    factors: dict[str, float] | None = None


def dump_model(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@router.get("/api/positive-ev")
def get_positive_ev(sport: str | None = None) -> dict[str, Any]:
    return positive_ev_feed(sport=sport)


@router.post("/api/arbitrage-check")
def arbitrage_check(payload: ArbitrageRequest) -> dict[str, Any]:
    try:
        return find_arbitrage(payload.outcomes, payload.bankroll)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/line-movement")
def line_movement(payload: LineMovementRequest) -> dict[str, Any]:
    try:
        return track_line_movement(dump_model(payload))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/bet-log")
def bet_log(payload: BetLogRequest) -> dict[str, Any]:
    try:
        return log_bet(dump_model(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/bet-performance")
def bet_performance() -> dict[str, Any]:
    return performance()


@router.post("/api/bankroll-sizing")
def bankroll_endpoint(payload: BankrollRequest) -> dict[str, Any]:
    try:
        return bankroll_sizing(payload.bankroll, payload.odds, payload.model_probability, payload.risk_level)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/alerts/create")
def alert_create(payload: AlertRequest) -> dict[str, Any]:
    try:
        return create_alert(dump_model(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/alerts")
def alerts() -> dict[str, Any]:
    return list_alerts()


@router.post("/api/model-builder/simulate")
def model_builder(payload: ModelBuilderRequest) -> dict[str, Any]:
    try:
        return simulate_model(dump_model(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
