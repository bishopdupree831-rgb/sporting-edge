from __future__ import annotations

from datetime import datetime, timezone

from app.services.odds_math import american_to_decimal


def kelly_fraction(model_probability: float, odds: int) -> float:
    decimal = american_to_decimal(odds)
    b = decimal - 1
    q = 1 - model_probability
    return max(0.0, (b * model_probability - q) / b)


def bankroll_sizing(bankroll: float, odds: int, model_probability: float, risk_level: str = "medium") -> dict:
    bankroll = float(bankroll)
    if bankroll <= 0:
        raise ValueError("bankroll must be positive")
    if not 0 < model_probability < 1:
        raise ValueError("model_probability must be between 0 and 1")
    risk_mult = {"low": 0.5, "medium": 1.0, "high": 1.5}.get(risk_level.lower(), 1.0)
    flat_unit = bankroll * 0.01 * risk_mult
    full_kelly = kelly_fraction(model_probability, odds) * bankroll
    half_kelly = full_kelly / 2
    max_exposure = bankroll * {"low": 0.02, "medium": 0.04, "high": 0.06}.get(risk_level.lower(), 0.04)
    recommended = min(flat_unit, half_kelly, max_exposure) if half_kelly > 0 else flat_unit * 0.5
    units = recommended / max(bankroll * 0.01, 1)
    return {
        "bankroll": bankroll,
        "flat_unit": round(flat_unit, 2),
        "half_kelly": round(half_kelly, 2),
        "full_kelly": round(full_kelly, 2),
        "max_exposure": round(max_exposure, 2),
        "recommended_stake": round(max(0, recommended), 2),
        "recommended_units": round(units, 2),
        "warning": "Max exposure reached; reduce stake size." if half_kelly > max_exposure else "",
        "verdict": f"Recommended stake: {round(units, 2)} units using half Kelly.",
        "data_freshness": datetime.now(timezone.utc).isoformat(),
    }
