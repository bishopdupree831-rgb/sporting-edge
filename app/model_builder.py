from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.odds_math import clamp, expected_value, implied_probability
from app.value_engine import confidence_grade, edge_score

DEFAULT_WEIGHTS = {
    "recent_form": 0.16,
    "matchup_history": 0.12,
    "injury_impact": 0.13,
    "pace": 0.09,
    "usage": 0.14,
    "line_movement": 0.12,
    "market_sharpness": 0.11,
    "weather": 0.05,
    "opponent_defense": 0.08,
}


def simulate_model(payload: dict[str, Any]) -> dict[str, Any]:
    weights = {**DEFAULT_WEIGHTS, **(payload.get("weights") or {})}
    factors = payload.get("factors") or {}
    odds = int(payload.get("odds", -110))
    total_weight = sum(max(0, float(value)) for value in weights.values()) or 1
    weighted = 0.0
    for key, weight in weights.items():
        factor = float(factors.get(key, 50))
        weighted += clamp(factor / 100, 0, 1) * max(0, float(weight))
    model_probability = clamp(weighted / total_weight, 0.01, 0.99)
    implied = implied_probability(odds)
    ev = expected_value(model_probability, odds)
    score = edge_score(model_probability, odds)
    return {
        "model_probability": round(model_probability, 4),
        "implied_probability": round(implied, 4),
        "ev": round(ev, 4),
        "edge_score": score,
        "grade": confidence_grade(score, ev),
        "weights": weights,
        "factors": factors,
        "verdict": f"This bet has {ev * 100:+.1f}% EV and a {score:.0f}/100 edge score.",
        "data_freshness": datetime.now(timezone.utc).isoformat(),
    }
