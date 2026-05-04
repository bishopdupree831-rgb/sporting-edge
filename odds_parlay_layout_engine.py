from __future__ import annotations

from typing import Any

from app.services.parlay_engine import SAMPLE_BOARD, analyze_slip, build_parlays


def card_badge(score: float) -> str:
    if score >= 0.72:
        return "premium"
    if score >= 0.62:
        return "playable"
    return "watch"


def layout_card(legs: list[dict[str, Any]], title: str = "Best available card") -> dict[str, Any]:
    analyzed = analyze_slip(legs)
    score = analyzed["slip"]["score"]
    return {
        "title": title,
        "score": score,
        "badge": card_badge(score),
        "summary": analyzed["slip"]["summary"],
        "legs": analyzed["legs"],
        "notes": analyzed["correlation_notes"],
        "style": {
            "accent": "#0b7a45",
            "gold": "#c89b2c",
            "density": "odds-card",
        },
    }


def default_cards(sport: str | None = None) -> list[dict[str, Any]]:
    board = [leg for leg in SAMPLE_BOARD if not sport or leg["sport"] == sport.upper()]
    if not board:
        board = SAMPLE_BOARD
    built = build_parlays(board)
    cards = list(built.values())[:2]
    return [layout_card(card["legs"], card.get("name", "Best available card")) for card in cards]
