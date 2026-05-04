from __future__ import annotations

from itertools import combinations
from math import prod
from typing import Any

from app.services.odds_math import american_to_decimal, expected_value, implied_probability, clamp


SAMPLE_BOARD: list[dict[str, Any]] = [
    {"id": "nba-brunson-pts", "sport": "NBA", "subject": "Jalen Brunson", "team": "NYK", "opponent": "IND", "market": "Points", "line": 27.5, "odds": -110, "model_probability": 0.59, "projection": 29.4, "l10_hit_rate": 0.70, "matchup_score": 63, "injury_score": 68},
    {"id": "nba-edwards-3pm", "sport": "NBA", "subject": "Anthony Edwards", "team": "MIN", "opponent": "DEN", "market": "Threes", "line": 2.5, "odds": +105, "model_probability": 0.55, "projection": 3.1, "l10_hit_rate": 0.60, "matchup_score": 58, "injury_score": 61},
    {"id": "nfl-lamb-rec", "sport": "NFL", "subject": "CeeDee Lamb", "team": "DAL", "opponent": "PHI", "market": "Receptions", "line": 6.5, "odds": -115, "model_probability": 0.57, "projection": 7.4, "l10_hit_rate": 0.70, "matchup_score": 66, "injury_score": 59},
    {"id": "mlb-betts-tb", "sport": "MLB", "subject": "Mookie Betts", "team": "LAD", "opponent": "ARI", "market": "Total Bases", "line": 1.5, "odds": -120, "model_probability": 0.56, "projection": 1.9, "l10_hit_rate": 0.62, "matchup_score": 62, "injury_score": 72},
    {"id": "mma-islam-td", "sport": "MMA", "subject": "Islam Makhachev", "team": "Makhachev", "opponent": "Tsarukyan", "market": "Takedowns", "line": 2.5, "odds": -125, "model_probability": 0.61, "projection": 3.4, "l10_hit_rate": 0.74, "matchup_score": 76, "injury_score": 64},
]


def edge_score(leg: dict[str, Any]) -> dict[str, Any]:
    probability = float(leg.get("model_probability", 0.52))
    odds = int(leg.get("odds", -110))
    ev = expected_value(probability, odds)
    implied = implied_probability(odds)
    projection = float(leg.get("projection", leg.get("line", 0)))
    line = float(leg.get("line", 0))
    gap = 0 if not line else abs(projection - line) / max(abs(line), 1)
    score = (
        clamp((probability - implied + 0.12) * 260, 0, 100) * 0.35
        + clamp(gap * 160, 0, 100) * 0.20
        + float(leg.get("matchup_score", 55)) * 0.15
        + float(leg.get("injury_score", 55)) * 0.15
        + float(leg.get("l10_hit_rate", 0.5)) * 100 * 0.15
    )
    grade = "A+" if score >= 85 else "A" if score >= 78 else "B" if score >= 68 else "C" if score >= 58 else "D"
    return {
        "edge_score": round(score, 1),
        "grade": grade,
        "ev": round(ev, 4),
        "model_probability": round(probability, 4),
        "implied_probability": round(implied, 4),
        "recommendation": "BET" if score >= 70 and ev > 0 else "LEAN" if score >= 58 else "PASS",
        "risk": "Low/Medium" if score >= 76 else "Medium" if score >= 62 else "High",
    }


def enrich_leg(leg: dict[str, Any]) -> dict[str, Any]:
    score = edge_score(leg)
    alt_line = float(leg.get("line", 0)) - 1 if "Points" in str(leg.get("market")) else float(leg.get("line", 0)) - 0.5
    return {
        **leg,
        **score,
        "decimal_odds": round(american_to_decimal(int(leg.get("odds", -110))), 3),
        "safer_alt": {"line": round(max(0, alt_line), 1), "note": "Lower line improves hit probability but usually reduces payout."},
        "freshness": "modeled/demo unless live provider rows are supplied",
    }


def correlation_notes(legs: list[dict[str, Any]]) -> list[str]:
    notes = []
    subjects = [str(leg.get("subject", "")).lower() for leg in legs]
    teams = [str(leg.get("team", "")).lower() for leg in legs]
    if len(subjects) != len(set(subjects)):
        notes.append("Duplicate player/fighter appears more than once. Check same-player correlation.")
    if len([team for team in teams if team]) != len(set(team for team in teams if team)):
        notes.append("Multiple legs share a team. Confirm the game script supports them together.")
    if not notes:
        notes.append("No obvious duplicate subject/team correlation detected.")
    return notes


def analyze_slip(legs: list[dict[str, Any]]) -> dict[str, Any]:
    enriched = [enrich_leg(leg) for leg in legs]
    weak = [leg for leg in enriched if leg["recommendation"] == "PASS" or leg["edge_score"] < 58]
    combined_probability = prod([leg["model_probability"] for leg in enriched]) if enriched else 0
    combined_decimal = prod([leg["decimal_odds"] for leg in enriched]) if enriched else 0
    ev = combined_probability * (combined_decimal - 1) - (1 - combined_probability) if enriched else 0
    avg_score = sum(leg["edge_score"] for leg in enriched) / len(enriched) / 100 if enriched else 0
    summary = "Use strongest singles first" if weak else "Parlay is researchable; confirm live news and lines."
    return {
        "legs": enriched,
        "weak_legs": weak,
        "correlation_notes": correlation_notes(enriched),
        "combined_probability": round(combined_probability, 4),
        "combined_decimal_odds": round(combined_decimal, 3),
        "expected_value_per_1u": round(ev, 4),
        "recommendation": summary,
        "bankroll_label": "Small stake only" if len(enriched) >= 4 or ev < 0 else "Standard 0.5u-1u research range",
        "slip": {
            "score": round(avg_score, 3),
            "summary": summary,
        },
    }


def build_parlays(board: list[dict[str, Any]], min_edge: float = 58) -> dict[str, Any]:
    enriched = [enrich_leg(leg) for leg in board]
    pool = [leg for leg in enriched if leg["edge_score"] >= min_edge]
    if len(pool) < 2:
        pool = sorted(enriched, key=lambda leg: leg["edge_score"], reverse=True)[:3]

    def slip(name: str, count: int, ordered: list[dict[str, Any]]) -> dict[str, Any]:
        selected = ordered[:count]
        analysis = analyze_slip(selected)
        return {"name": name, **analysis}

    by_score = sorted(pool, key=lambda leg: leg["edge_score"], reverse=True)
    by_prob = sorted(pool, key=lambda leg: leg["model_probability"], reverse=True)
    by_odds = sorted(pool, key=lambda leg: leg["decimal_odds"], reverse=True)
    same_game = next((list(combo) for combo in combinations(by_score, 2) if combo[0].get("team") == combo[1].get("team")), by_score[:2])
    return {
        "safe": slip("Safe 2-leg", 2, by_prob),
        "balanced": slip("Balanced 3-leg", 3, by_score),
        "correlated": {"name": "Correlated 2-leg", **analyze_slip(same_game)},
        "lotto": slip("Lotto", min(5, len(by_odds)), by_odds),
    }


def alt_ladder(leg: dict[str, Any]) -> dict[str, Any]:
    line = float(leg.get("line", 0))
    probability = float(leg.get("model_probability", 0.55))
    side = str(leg.get("side", "over")).lower()
    ladder = []
    for step in [-2, -1, 0, 1, 2]:
        adjusted = max(0, line + step * 0.5)
        prob = probability - step * 0.035 if side == "over" else probability + step * 0.035
        ladder.append({
            "line": round(adjusted, 1),
            "model_probability": round(clamp(prob, 0.05, 0.95), 4),
            "label": "safer" if step < 0 else "posted" if step == 0 else "higher payout",
        })
    return {"subject": leg.get("subject"), "market": leg.get("market"), "ladder": ladder}
