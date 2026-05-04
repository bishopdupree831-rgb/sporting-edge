from __future__ import annotations

from typing import Any

from app.intelligence.stat_models import clamp, context_score
from app.services.odds_math import expected_value, implied_probability


def project_prop(payload: dict[str, Any]) -> dict[str, Any]:
    sport = str(payload.get("sport") or "NBA").upper()
    player = str(payload.get("player") or payload.get("name") or "Selected player")
    market = str(payload.get("market") or "Points")
    line = float(payload.get("line") or 0)
    odds = int(payload.get("odds") or -110)
    context = context_score(payload)
    base_projection = float(payload.get("projection") or (line * (1.03 + context.total * 0.18)))
    volatility = 0.12 if sport in {"NBA", "NHL"} else 0.16 if sport in {"NFL", "MLB"} else 0.2
    true_probability = clamp(0.5 + (base_projection - line) / max(line, 1) * 0.45 + (context.total - 0.55) * 0.28, 0.08, 0.92)
    implied = implied_probability(odds)
    ev = expected_value(true_probability, odds)
    edge = true_probability - implied
    confidence = clamp(true_probability * 0.62 + context.total * 0.38 - volatility * 0.1)
    return {
        "player": player,
        "sport": sport,
        "market": market,
        "line": line,
        "odds": odds,
        "projection": round(base_projection, 2),
        "true_probability": round(true_probability, 3),
        "implied_probability": round(implied, 3),
        "edge": round(edge, 3),
        "ev": round(ev, 3),
        "confidence": round(confidence, 3),
        "context": context.__dict__ | {"total": context.total},
        "recommendation": "Research candidate" if edge > 0.03 and confidence > 0.55 else "Watch list",
    }


def trend_card(payload: dict[str, Any]) -> dict[str, Any]:
    projection = project_prop(payload)
    player = projection["player"]
    market = projection["market"]
    return {
        "title": f"{player} {market} trend",
        "score": round(projection["confidence"] * 100),
        "summary": (
            f"Projection {projection['projection']} vs line {projection['line']} with "
            f"{round(projection['edge'] * 100, 1)}% edge after form, matchup, environment, and lineup risk."
        ),
        "tags": [projection["sport"], projection["recommendation"], f"EV {projection['ev']}"],
        "projection": projection,
    }


def daily_card(sport: str = "NBA") -> dict[str, Any]:
    templates = {
        "NBA": {"player": "High-usage guard", "market": "Points", "line": 24.5, "recent": [26, 29, 20, 31, 28]},
        "NFL": {"player": "Primary receiver", "market": "Receiving Yards", "line": 64.5, "recent": [72, 81, 55, 69, 88]},
        "MLB": {"player": "Leadoff hitter", "market": "Total Bases", "line": 1.5, "recent": [2, 1, 3, 0, 2]},
        "NHL": {"player": "Top-line winger", "market": "Shots", "line": 2.5, "recent": [3, 5, 2, 4, 3]},
        "MMA": {"player": "Pressure grappler", "market": "Takedowns", "line": 1.5, "recent": [2, 3, 1, 4, 2]},
    }
    payload = templates.get(sport.upper(), templates["NBA"]) | {"sport": sport.upper(), "odds": -110}
    return trend_card(payload)
