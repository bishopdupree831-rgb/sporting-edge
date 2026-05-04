from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.providers import live_provider_connected, provider_statuses
from app.providers.odds_provider import fetch_live_odds, flatten_odds_events
from app.services.odds_math import clamp, expected_value, fair_american_odds, implied_probability

MANUAL_PROVIDER_MESSAGE = "Live provider not connected. Real-time mode unavailable."


def no_vig_probabilities(odds_list: list[int]) -> list[float]:
    if not odds_list:
        return []
    implied = [implied_probability(int(odds)) for odds in odds_list]
    total = sum(implied)
    if total <= 0:
        raise ValueError("odds_list produced invalid implied probabilities")
    return [prob / total for prob in implied]


def confidence_grade(edge_score: float, ev: float) -> str:
    if ev <= 0 or edge_score < 50:
        return "PASS"
    if edge_score >= 90:
        return "A+"
    if edge_score >= 82:
        return "A"
    if edge_score >= 74:
        return "B"
    if edge_score >= 64:
        return "C"
    return "D"


def edge_score(model_probability: float, sportsbook_odds: int, no_vig_probability: float | None = None) -> float:
    implied = implied_probability(sportsbook_odds)
    baseline = no_vig_probability if no_vig_probability is not None else implied
    raw_edge = model_probability - baseline
    ev = expected_value(model_probability, sportsbook_odds)
    return round(clamp(50 + raw_edge * 420 + ev * 60, 0, 100), 1)


def analyze_value_bet(row: dict[str, Any]) -> dict[str, Any]:
    model_probability = float(row.get("model_probability", 0))
    odds = int(row.get("odds", 0))
    if not 0 < model_probability < 1:
        raise ValueError("model_probability must be between 0 and 1")
    if odds == 0:
        raise ValueError("odds cannot be zero")
    paired_odds = row.get("market_odds")
    no_vig_probability = None
    if isinstance(paired_odds, list) and len(paired_odds) >= 2:
        no_vig_probability = no_vig_probabilities([int(item) for item in paired_odds])[0]
    implied = implied_probability(odds)
    ev = expected_value(model_probability, odds)
    score = edge_score(model_probability, odds, no_vig_probability)
    grade = confidence_grade(score, ev)
    return {
        "sport": row.get("sport", "Unknown"),
        "market": row.get("market", "Unknown market"),
        "bet": row.get("bet") or row.get("selection") or "Manual entry",
        "sportsbook": row.get("sportsbook", "manual"),
        "odds": odds,
        "model_probability": round(model_probability, 4),
        "implied_probability": round(implied, 4),
        "no_vig_probability": round(no_vig_probability, 4) if no_vig_probability is not None else None,
        "fair_odds": fair_american_odds(model_probability),
        "ev": round(ev, 4),
        "edge_score": score,
        "grade": grade,
        "verdict": f"This bet has {ev * 100:+.1f}% EV and a {score:.0f}/100 edge score." if ev > 0 else "No positive EV at the current price.",
        "data_freshness": datetime.now(timezone.utc).isoformat(),
    }


def _rows_from_live_odds(sport: str | None = None) -> list[dict[str, Any]]:
    if not sport:
        return []
    odds = fetch_live_odds(sport=sport, include_player_props=True)
    rows = flatten_odds_events(odds.get("events", []))
    # A real model probability requires stats/news inputs. Until that model is trained,
    # do not invent probabilities; only rows with provider/model probabilities should enter +EV.
    return [row for row in rows if "model_probability" in row]


def positive_ev_feed(rows: list[dict[str, Any]] | None = None, sport: str | None = None) -> dict[str, Any]:
    connected = live_provider_connected()
    if not rows and connected and sport:
        try:
            rows = _rows_from_live_odds(sport)
        except Exception as exc:
            return {
                "provider_mode": "provider-error",
                "provider_message": str(exc),
                "data_freshness": datetime.now(timezone.utc).isoformat(),
                "provider_sources": provider_statuses(),
                "bets": [],
            }
    if not rows:
        return {
            "provider_mode": "live-provider" if connected else "unavailable",
            "provider_message": "No model-probability feed connected for +EV ranking." if connected else MANUAL_PROVIDER_MESSAGE,
            "data_freshness": datetime.now(timezone.utc).isoformat(),
            "provider_sources": provider_statuses(),
            "bets": [],
        }
    analyzed = []
    for row in rows:
        if sport and str(row.get("sport", "")).upper() != sport.upper():
            continue
        item = analyze_value_bet(row)
        if item["ev"] > 0:
            analyzed.append(item)
    analyzed.sort(key=lambda item: (item["ev"], item["edge_score"]), reverse=True)
    return {
        "provider_mode": "manual-input" if not connected else "live-provider-enriched",
        "provider_message": "" if connected else MANUAL_PROVIDER_MESSAGE,
        "data_freshness": datetime.now(timezone.utc).isoformat(),
        "provider_sources": provider_statuses(),
        "bets": analyzed,
    }
