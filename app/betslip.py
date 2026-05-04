from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.providers.sportsbook_provider import approved_transfer_connected, sportsbook_links
from app.services.odds_math import american_to_decimal, expected_value, fair_american_odds, implied_probability

DIRECT_UNAVAILABLE = "Direct sportsbook connection not available. Use copy betslip."


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def decimal_to_american(decimal: float) -> int:
    if decimal <= 1:
        raise ValueError("decimal odds must be greater than 1")
    if decimal >= 2:
        return round((decimal - 1) * 100)
    return round(-100 / (decimal - 1))


def normalize_leg(leg: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(leg, dict):
        raise ValueError("each leg must be an object")
    selection = str(leg.get("selection") or leg.get("pick") or "").strip()
    if not selection:
        raise ValueError("each leg needs a selection")
    odds = leg.get("odds")
    try:
        odds = int(odds)
    except (TypeError, ValueError):
        raise ValueError("each leg needs valid American odds") from None
    if odds == 0:
        raise ValueError("odds cannot be zero")
    normalized = {
        "sport": str(leg.get("sport") or "Unknown").upper(),
        "sportsbook": str(leg.get("sportsbook") or "Manual").strip(),
        "event_id": str(leg.get("event_id") or ""),
        "game": str(leg.get("game") or leg.get("matchup") or ""),
        "market_type": str(leg.get("market_type") or "unknown"),
        "market_group": str(leg.get("market_group") or leg.get("market") or "unknown"),
        "selection": selection,
        "player_name": leg.get("player_name"),
        "team": leg.get("team"),
        "opponent": leg.get("opponent"),
        "side": leg.get("side"),
        "line": leg.get("line"),
        "odds": odds,
        "start_time": leg.get("start_time"),
        "last_updated": leg.get("last_updated") or now_iso(),
        "source": leg.get("source") or "manual",
    }
    if leg.get("model_probability") is not None:
        try:
            normalized["model_probability"] = min(0.99, max(0.01, float(leg["model_probability"])))
        except (TypeError, ValueError):
            pass
    return normalized


def combined_decimal_odds(legs: list[dict[str, Any]]) -> float:
    decimal = 1.0
    for leg in legs:
        decimal *= american_to_decimal(int(leg["odds"]))
    return decimal


def combined_model_probability(legs: list[dict[str, Any]]) -> float | None:
    probability = 1.0
    for leg in legs:
        if leg.get("model_probability") is None:
            return None
        probability *= float(leg["model_probability"])
    return max(0.001, min(0.999, probability))


def detect_conflicts(legs: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()
    sides: dict[str, str] = {}
    books = {leg.get("sportsbook") for leg in legs if leg.get("sportsbook")}
    if len(books) > 1:
        warnings.append("Mixed sportsbooks detected. Verify every leg is available at the selected book.")
    for leg in legs:
        key = "|".join(str(leg.get(k) or "").lower() for k in ("event_id", "market_group", "selection"))
        if key in seen:
            warnings.append(f"Duplicate leg detected: {leg['selection']}")
        seen.add(key)
        side_key = "|".join(str(leg.get(k) or "").lower() for k in ("event_id", "player_name", "team", "market_group"))
        side = str(leg.get("side") or "").lower()
        if side_key.strip("|") and side:
            existing = sides.get(side_key)
            if existing and existing != side:
                warnings.append(f"Conflicting over/under legs for {leg.get('player_name') or leg.get('team') or leg['selection']}.")
            sides[side_key] = side
    if len(legs) >= 4:
        warnings.append("Four or more legs increases variance. Consider trimming to the strongest edges.")
    return list(dict.fromkeys(warnings))


def correlation_warnings(legs: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    by_event: dict[str, list[dict[str, Any]]] = {}
    for leg in legs:
        event_key = leg.get("event_id") or leg.get("game") or "unknown"
        by_event.setdefault(str(event_key), []).append(leg)
    for event, event_legs in by_event.items():
        if len(event_legs) < 2:
            continue
        markets = " ".join(str(leg.get("market_group") or "").lower() for leg in event_legs)
        if "moneyline" in markets and ("spread" in markets or "team total" in markets):
            warnings.append(f"Same-game correlation in {event}: moneyline/spread/team total legs may move together.")
        if "passing" in markets and "receiving" in markets:
            warnings.append(f"Positive QB/receiver correlation in {event}; useful but raises same-game exposure.")
        if "under" in " ".join(str(leg.get("side") or "").lower() for leg in event_legs) and "over" in " ".join(str(leg.get("side") or "").lower() for leg in event_legs):
            warnings.append(f"Mixed over/under exposure in {event}; check game-script assumptions.")
    return warnings


def edge_score(model_probability: float | None, implied: float, warnings: list[str]) -> int | None:
    if model_probability is None:
        return None
    edge = model_probability - implied
    score = round(50 + edge * 250 - min(len(warnings), 5) * 4)
    return max(0, min(100, score))


def safer_alt_suggestions(legs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for leg in legs:
        line = leg.get("line")
        side = str(leg.get("side") or "").lower()
        try:
            line_float = float(line)
        except (TypeError, ValueError):
            continue
        if side == "over":
            alt_line = max(0, line_float - 1)
        elif side == "under":
            alt_line = line_float + 1
        else:
            continue
        suggestions.append({
            "selection": leg["selection"],
            "suggestion": f"Check {side} {alt_line:g} as a safer alternate line if the book offers it.",
        })
    return suggestions[:5]


def create_betslip(legs: list[dict[str, Any]], stake: float = 10, sport: str | None = None, sportsbook: str | None = None) -> dict[str, Any]:
    if not legs:
        raise ValueError("betslip needs at least one leg")
    try:
        stake = float(stake)
    except (TypeError, ValueError):
        raise ValueError("stake must be numeric") from None
    if stake <= 0:
        raise ValueError("stake must be greater than zero")
    normalized_legs = [normalize_leg(leg) for leg in legs]
    decimal = combined_decimal_odds(normalized_legs)
    american = decimal_to_american(decimal)
    implied = 1 / decimal
    model_probability = combined_model_probability(normalized_legs)
    warnings = detect_conflicts(normalized_legs) + correlation_warnings(normalized_legs)
    ev = expected_value(model_probability, american, stake=stake) if model_probability is not None else None
    score = edge_score(model_probability, implied, warnings)
    export_text = export_text_slip(normalized_legs, stake, american, model_probability, ev)
    slip_id = str(uuid.uuid4())
    return {
        "id": slip_id,
        "sport": sport or normalized_legs[0].get("sport") or "Mixed",
        "sportsbook": sportsbook or normalized_legs[0].get("sportsbook") or "Mixed",
        "legs": normalized_legs,
        "stake": stake,
        "combined_decimal_odds": round(decimal, 4),
        "combined_odds": f"{american:+d}",
        "model_probability": model_probability,
        "implied_probability": implied,
        "expected_value": ev,
        "edge_score": score,
        "fair_odds": fair_american_odds(model_probability) if model_probability is not None else None,
        "warnings": list(dict.fromkeys(warnings)),
        "safer_alt_suggestions": safer_alt_suggestions(normalized_legs),
        "export_text": export_text,
        "share_url": f"/share/betslip/{slip_id}",
        "data_freshness": now_iso(),
    }


def analyze_betslip(legs: list[dict[str, Any]], stake: float = 10, sport: str | None = None, sportsbook: str | None = None) -> dict[str, Any]:
    slip = create_betslip(legs, stake=stake, sport=sport, sportsbook=sportsbook)
    if slip["model_probability"] is None:
        slip["warnings"].append("Model probability unavailable without a connected model feed or leg probabilities.")
        slip["verdict"] = "Price can be calculated, but EV needs model probabilities."
    elif slip["expected_value"] and slip["expected_value"] > 0:
        slip["verdict"] = f"This bet has positive EV and a {slip['edge_score']}/100 edge score."
    else:
        slip["verdict"] = "No positive EV detected at the current inputs."
    return slip


def export_text_slip(legs: list[dict[str, Any]], stake: float, combined_odds: int, model_probability: float | None, ev: float | None) -> str:
    lines = ["Sporting Edge Betslip", f"Stake: ${stake:g}", f"Combined odds: {combined_odds:+d}"]
    if model_probability is not None:
        lines.append(f"Model probability: {model_probability:.1%}")
    if ev is not None:
        lines.append(f"Expected value: ${ev:.2f}")
    lines.append("")
    for index, leg in enumerate(legs, 1):
        lines.append(f"{index}. {leg['selection']} ({leg['sportsbook']} {leg['odds']:+d})")
    lines.append("")
    lines.append("Direct sportsbook connection not available. Use copy betslip.")
    return "\n".join(lines)


def export_betslip(legs: list[dict[str, Any]], stake: float = 10, sport: str | None = None, sportsbook: str | None = None) -> dict[str, Any]:
    slip = analyze_betslip(legs, stake=stake, sport=sport, sportsbook=sportsbook)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "sport", "sportsbook", "stake", "combined_odds", "model_probability", "implied_probability", "expected_value", "edge_score"])
    writer.writerow([
        slip["id"], slip["sport"], slip["sportsbook"], slip["stake"], slip["combined_odds"],
        slip["model_probability"], slip["implied_probability"], slip["expected_value"], slip["edge_score"],
    ])
    links = sportsbook_links()
    slip["plain_text"] = slip["export_text"]
    slip["json_betslip"] = json.dumps(slip, indent=2, default=str)
    slip["csv_row"] = output.getvalue()
    slip["draftkings_link"] = links.get("DraftKings")
    slip["fanduel_link"] = links.get("FanDuel")
    return slip


def send_to_book(legs: list[dict[str, Any]], stake: float = 10, sportsbook: str | None = None) -> dict[str, Any]:
    slip = analyze_betslip(legs, stake=stake, sportsbook=sportsbook)
    if not approved_transfer_connected():
        return {
            "ok": False,
            "message": DIRECT_UNAVAILABLE,
            "manual_instructions": "Copy this slip, open your sportsbook, verify every line and price, then place manually if you choose.",
            "betslip": slip,
        }
    return {
        "ok": True,
        "message": "Approved sportsbook transfer is connected. A pending slip can be created, but no wager was placed.",
        "status": "pending",
        "betslip": slip,
    }
