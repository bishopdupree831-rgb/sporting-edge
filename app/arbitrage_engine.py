from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.providers import live_provider_connected, provider_statuses
from app.services.odds_math import american_to_decimal, implied_probability
from app.value_engine import MANUAL_PROVIDER_MESSAGE


def find_arbitrage(outcomes: list[dict[str, Any]], bankroll: float = 1000.0) -> dict[str, Any]:
    if len(outcomes) < 2:
        raise ValueError("at least two outcomes are required")
    bankroll = float(bankroll)
    if bankroll <= 0:
        raise ValueError("bankroll must be positive")
    enriched = []
    inv_total = 0.0
    for outcome in outcomes:
        odds = int(outcome.get("odds", 0))
        if odds == 0:
            raise ValueError("odds cannot be zero")
        decimal = american_to_decimal(odds)
        inv = 1 / decimal
        inv_total += inv
        enriched.append({**outcome, "decimal_odds": round(decimal, 4), "implied_probability": round(implied_probability(odds), 4), "_inverse": inv})
    is_arb = inv_total < 1
    stake_plan = []
    guaranteed_return = 0.0
    if is_arb:
        for outcome in enriched:
            stake = bankroll * outcome["_inverse"] / inv_total
            payout = stake * outcome["decimal_odds"]
            guaranteed_return = payout if not guaranteed_return else min(guaranteed_return, payout)
            stake_plan.append({
                "sportsbook": outcome.get("sportsbook", "manual"),
                "selection": outcome.get("selection", "Outcome"),
                "odds": outcome.get("odds"),
                "stake": round(stake, 2),
                "payout": round(payout, 2),
            })
    profit = guaranteed_return - bankroll if is_arb else 0
    profit_pct = profit / bankroll if bankroll else 0
    connected = live_provider_connected()
    return {
        "is_arbitrage": is_arb,
        "arbitrage_percentage": round((1 - inv_total) * 100, 3),
        "guaranteed_profit_pct": round(profit_pct * 100, 3),
        "required_bankroll": bankroll,
        "stake_split": stake_plan,
        "verdict": f"This arbitrage locks {profit_pct * 100:.1f}% profit if staked correctly." if is_arb else "No guaranteed-profit arbitrage at these prices.",
        "data_freshness": datetime.now(timezone.utc).isoformat(),
        "provider_sources": provider_statuses(),
        "provider_message": "" if connected else MANUAL_PROVIDER_MESSAGE,
    }
