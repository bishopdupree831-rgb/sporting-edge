from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.parlay_engine import SAMPLE_BOARD, alt_ladder, analyze_slip, build_parlays

router = APIRouter(prefix="/api/workbench", tags=["parlay-workbench"])


class SlipRequest(BaseModel):
    legs: list[dict[str, Any]]


class BuildRequest(BaseModel):
    board: list[dict[str, Any]] | None = None
    legs: list[dict[str, Any]] | None = None
    count: int = Field(3, ge=1, le=8)
    target_legs: int | None = Field(None, ge=1, le=8)
    min_edge: float = Field(58, ge=0, le=100)


class AltRequest(BaseModel):
    leg: dict[str, Any]


@router.get("/sample-board")
def sample_board() -> dict[str, Any]:
    return {"source": "modeled-demo-board", "board": SAMPLE_BOARD, "note": "Connect licensed live feeds for production odds."}


@router.post("/analyze-slip")
def analyze_betslip(payload: SlipRequest) -> dict[str, Any]:
    return analyze_slip(payload.legs)


@router.post("/build-parlays")
def build_workbench_parlays(payload: BuildRequest) -> dict[str, Any]:
    board = payload.board or payload.legs or SAMPLE_BOARD
    built = build_parlays(board, payload.min_edge)
    cards = [
        {"title": value.get("name", key.title()), **value}
        for key, value in built.items()
    ]
    return {"cards": cards[: payload.count], "raw": built}


@router.post("/alt-ladder")
def build_alt_ladder(payload: AltRequest) -> dict[str, Any]:
    return alt_ladder(payload.leg)
