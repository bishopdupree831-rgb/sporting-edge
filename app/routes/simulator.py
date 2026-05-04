from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.simulator_engine import (
    analyze_betslip,
    analyze_line_movement,
    bankroll_plan,
    build_edge_score,
    build_parlay,
    formula_snapshot,
    recap_learning,
    simulate_hit_probability,
)

router = APIRouter(prefix="/api/simulator", tags=["simulator"])


def dump_model(model: BaseModel) -> dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


class EdgeRequest(BaseModel):
    probability: float = Field(..., ge=0, le=1)
    odds: int = -110
    projection: float
    line: float
    matchup_score: float = Field(50, ge=0, le=100)
    injury_score: float = Field(50, ge=0, le=100)
    line_movement_score: float = Field(50, ge=0, le=100)
    data_quality_score: float = Field(55, ge=0, le=100)


class PropRequest(BaseModel):
    sport: str = "NBA"
    subject: str
    market: str
    line: float
    odds: int = -110
    side: str = "over"
    projection: float
    recent_values: list[float] = []
    matchup_score: float = 50
    injury_score: float = 50
    line_movement_score: float = 50
    data_quality_score: float = 55


class ParlayRequest(BaseModel):
    style: str = "balanced"
    legs: list[dict[str, Any]]


class LineMovementRequest(BaseModel):
    open_line: float
    current_line: float
    open_odds: int = -110
    current_odds: int = -110
    public_bet_pct: float | None = None
    money_pct: float | None = None


class BetSlipRequest(BaseModel):
    legs: list[dict[str, Any]]


class BankrollRequest(BaseModel):
    bankroll: float = Field(..., gt=0)
    edge_score: float = Field(..., ge=0, le=100)
    risk: str = "Medium"
    max_daily_exposure_pct: float = Field(0.08, gt=0, le=0.25)


class RecapRequest(BaseModel):
    predictions: list[dict[str, Any]]


@router.get("/health")
def simulator_health() -> dict[str, Any]:
    return {"ok": True, "module": "full-system-simulator", "version": "1.0"}


@router.get("/formula")
def simulator_formula() -> dict[str, Any]:
    return formula_snapshot()


@router.post("/edge")
def simulator_edge(payload: EdgeRequest) -> dict[str, Any]:
    return build_edge_score(**dump_model(payload))


@router.post("/prop")
def simulator_prop(payload: PropRequest) -> dict[str, Any]:
    sim = simulate_hit_probability(
        projection=payload.projection,
        line=payload.line,
        recent_values=payload.recent_values,
        side=payload.side,
        market=payload.market,
    )
    edge = build_edge_score(
        probability=sim["hit_probability"],
        odds=payload.odds,
        projection=sim["projection"],
        line=payload.line,
        matchup_score=payload.matchup_score,
        injury_score=payload.injury_score,
        line_movement_score=payload.line_movement_score,
        data_quality_score=payload.data_quality_score,
    )
    return {
        "sport": payload.sport,
        "subject": payload.subject,
        "market": payload.market,
        "simulation": sim,
        "edge": edge,
        "source_mode": "modeled",
        "responsible_note": "Research and entertainment only. Results are not guaranteed picks.",
    }


@router.post("/parlay")
def simulator_parlay(payload: ParlayRequest) -> dict[str, Any]:
    return build_parlay(payload.legs, payload.style)


@router.post("/line-movement")
def simulator_line_movement(payload: LineMovementRequest) -> dict[str, Any]:
    return analyze_line_movement(**dump_model(payload))


@router.post("/betslip")
def simulator_betslip(payload: BetSlipRequest) -> dict[str, Any]:
    return analyze_betslip(payload.legs)


@router.post("/bankroll")
def simulator_bankroll(payload: BankrollRequest) -> dict[str, Any]:
    return bankroll_plan(**dump_model(payload))


@router.post("/recap")
def simulator_recap(payload: RecapRequest) -> dict[str, Any]:
    return recap_learning(payload.predictions)
