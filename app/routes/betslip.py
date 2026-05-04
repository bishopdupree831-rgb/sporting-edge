from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.betslip import analyze_betslip, create_betslip, export_betslip, send_to_book

router = APIRouter(tags=["betslip"])


class BetSlipRequest(BaseModel):
    sport: str | None = None
    sportsbook: str | None = None
    legs: list[dict[str, Any]] = Field(default_factory=list)
    stake: float = Field(10, gt=0)


def dump_model(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@router.post("/api/betslip")
def create_slip(payload: BetSlipRequest) -> dict[str, Any]:
    try:
        data = dump_model(payload)
        return create_betslip(data["legs"], stake=data["stake"], sport=data.get("sport"), sportsbook=data.get("sportsbook"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/betslip/analyze")
def analyze_slip(payload: BetSlipRequest) -> dict[str, Any]:
    try:
        data = dump_model(payload)
        return analyze_betslip(data["legs"], stake=data["stake"], sport=data.get("sport"), sportsbook=data.get("sportsbook"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/betslip/export")
def export_slip(payload: BetSlipRequest) -> dict[str, Any]:
    try:
        data = dump_model(payload)
        return export_betslip(data["legs"], stake=data["stake"], sport=data.get("sport"), sportsbook=data.get("sportsbook"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/betslip/send-to-book")
def send_slip_to_book(payload: BetSlipRequest) -> dict[str, Any]:
    try:
        data = dump_model(payload)
        return send_to_book(data["legs"], stake=data["stake"], sportsbook=data.get("sportsbook"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
