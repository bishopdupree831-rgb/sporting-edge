from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.odds_math import implied_probability

BET_LOG: list[dict[str, Any]] = []


def calculate_clv(odds_taken: int, closing_odds: int | None = None, line_taken: float | None = None, closing_line: float | None = None) -> dict[str, float]:
    odds_clv = 0.0
    if closing_odds:
        odds_clv = implied_probability(closing_odds) - implied_probability(odds_taken)
    line_clv = 0.0
    if line_taken is not None and closing_line is not None:
        line_clv = (closing_line - line_taken) / max(abs(line_taken), 1)
    return {"odds_clv": round(odds_clv, 4), "line_clv": round(line_clv, 4), "clv": round(odds_clv + line_clv, 4)}


def log_bet(payload: dict[str, Any]) -> dict[str, Any]:
    odds_taken = int(payload.get("odds_taken", payload.get("odds", 0)))
    if odds_taken == 0:
        raise ValueError("odds_taken cannot be zero")
    stake_units = float(payload.get("units", 1))
    outcome = str(payload.get("outcome", "pending")).lower()
    profit = 0.0
    if outcome == "win":
        profit = stake_units * (abs(odds_taken) / 100 if odds_taken > 0 else 100 / abs(odds_taken))
    elif outcome == "loss":
        profit = -stake_units
    clv = calculate_clv(
        odds_taken,
        payload.get("closing_odds"),
        payload.get("line_taken"),
        payload.get("closing_line"),
    )
    row = {
        "id": len(BET_LOG) + 1,
        "sport": payload.get("sport", "Unknown"),
        "bet": payload.get("bet", "Manual bet"),
        "market": payload.get("market", "Unknown"),
        "sportsbook": payload.get("sportsbook", "manual"),
        "odds_taken": odds_taken,
        "closing_odds": payload.get("closing_odds"),
        "line_taken": payload.get("line_taken"),
        "closing_line": payload.get("closing_line"),
        "units": stake_units,
        "outcome": outcome,
        "profit_units": round(profit, 3),
        **clv,
        "verdict": f"You beat the closing line by {clv['clv'] * 100:.1f}%.",
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    BET_LOG.append(row)
    return row


def performance() -> dict[str, Any]:
    settled = [row for row in BET_LOG if row["outcome"] in {"win", "loss"}]
    wins = sum(1 for row in settled if row["outcome"] == "win")
    losses = sum(1 for row in settled if row["outcome"] == "loss")
    units = sum(row["profit_units"] for row in BET_LOG)
    risked = sum(row["units"] for row in BET_LOG if row["outcome"] in {"win", "loss"})
    avg_clv = sum(row["clv"] for row in BET_LOG) / len(BET_LOG) if BET_LOG else 0
    return {
        "bets": BET_LOG,
        "record": {"wins": wins, "losses": losses, "pending": len(BET_LOG) - len(settled)},
        "roi": round(units / risked, 4) if risked else 0,
        "units": round(units, 3),
        "average_clv": round(avg_clv, 4),
        "data_freshness": datetime.now(timezone.utc).isoformat(),
    }
