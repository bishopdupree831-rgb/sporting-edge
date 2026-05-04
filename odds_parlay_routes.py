from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from odds_parlay_layout_engine import default_cards, layout_card

router = APIRouter()


class OddsCardPayload(BaseModel):
    title: str = "Custom odds-style card"
    legs: list[dict[str, Any]]


def dump_model(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@router.get("/api/odds-style/parlay-cards")
def parlay_cards(sport: str | None = None) -> dict[str, Any]:
    return {"cards": default_cards(sport)}


@router.post("/api/odds-style/build-card")
def build_card(payload: OddsCardPayload) -> dict[str, Any]:
    data = dump_model(payload)
    return layout_card(data["legs"], data["title"])
