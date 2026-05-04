from __future__ import annotations

from math import prod
from statistics import mean, pstdev
from typing import Any
import random


def american_to_decimal(odds: int) -> float:
    if odds == 0:
        raise ValueError("odds cannot be 0")
    return 1 + (odds / 100 if odds > 0 else 100 / abs(odds))


def implied_probability(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def no_vig_probs(odds_a: int, odds_b: int) -> tuple[float, float]:
    pa = implied_probability(odds_a)
    pb = implied_probability(odds_b)
    total = pa + pb
    if total <= 0:
        return 0.5, 0.5
    return pa / total, pb / total


def expected_value(probability: float, odds: int, stake: float = 1.0) -> float:
    dec = american_to_decimal(odds)
    profit = stake * (dec - 1)
    loss = stake
    return probability * profit - (1 - probability) * loss


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def confidence_tier(score: float) -> str:
    if score >= 85:
        return "A+"
    if score >= 78:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def risk_tier(score: float, probability: float, ev: float) -> str:
    if score >= 78 and probability >= 0.57 and ev > 0.05:
        return "Low/Medium"
    if score >= 65 and probability >= 0.53:
        return "Medium"
    if score >= 55:
        return "High"
    return "Pass"


def market_volatility(market: str) -> float:
    m = market.lower()
    if any(x in m for x in ["first", "1q", "quarter", "touchdown", "home run", "ko", "round"]):
        return 1.20
    if any(x in m for x in ["points", "rebounds", "assists", "shots", "strikeouts", "yards"]):
        return 1.00
    if any(x in m for x in ["moneyline", "spread", "total"]):
        return 0.90
    return 1.05


def simulate_hit_probability(
    projection: float,
    line: float,
    recent_values: list[float] | None = None,
    side: str = "over",
    market: str = "",
    runs: int = 3500,
) -> dict[str, Any]:
    recent_values = recent_values or []
    if recent_values:
        base_sd = pstdev(recent_values) if len(recent_values) >= 2 else max(abs(projection) * 0.18, 1.0)
        avg_recent = mean(recent_values)
        projection = projection * 0.70 + avg_recent * 0.30
    else:
        base_sd = max(abs(projection) * 0.18, 1.0)

    sd = max(base_sd * market_volatility(market), 0.65)
    hits = 0
    samples: list[float] = []
    runs = max(100, int(runs))

    for _ in range(runs):
        value = random.gauss(projection, sd)
        samples.append(value)
        if side.lower() in ("under", "no"):
            hits += value < line
        else:
            hits += value > line

    probability = hits / runs
    ordered = sorted(samples)
    return {
        "projection": round(projection, 2),
        "line": line,
        "side": side,
        "hit_probability": round(probability, 4),
        "sample_mean": round(mean(samples), 2),
        "sample_sd": round(sd, 2),
        "p10": round(ordered[int(runs * 0.10)], 2),
        "p50": round(ordered[int(runs * 0.50)], 2),
        "p90": round(ordered[int(runs * 0.90)], 2),
        "runs": runs,
    }


def build_edge_score(
    probability: float | dict[str, Any],
    odds: int | None = None,
    projection: float | None = None,
    line: float | None = None,
    matchup_score: float = 50,
    injury_score: float = 50,
    line_movement_score: float = 50,
    data_quality_score: float = 55,
) -> dict[str, Any]:
    if isinstance(probability, dict):
        payload = probability
        probability = float(payload.get("true_probability", payload.get("model_probability", payload.get("probability", 0.52))))
        odds = int(payload.get("odds", -110) if odds is None else odds)
        projection = float(payload.get("projection", payload.get("line", 0)) if projection is None else projection)
        line = float(payload.get("line", 0) if line is None else line)
        matchup_score = float(payload.get("matchup_score", matchup_score))
        injury_score = float(payload.get("injury_score", injury_score))
        line_movement_score = float(payload.get("line_movement_score", line_movement_score))
        data_quality_score = float(payload.get("data_quality_score", data_quality_score))
    odds = int(-110 if odds is None else odds)
    projection = float(0 if projection is None else projection)
    line = float(0 if line is None else line)
    imp = implied_probability(odds)
    ev = expected_value(probability, odds)
    projection_gap = 0 if line == 0 else abs((projection - line) / max(abs(line), 1))
    gap_score = clamp(projection_gap * 180, 0, 100)

    edge_margin = probability - imp
    ev_score = clamp((ev + 0.18) * 220, 0, 100)
    prob_score = clamp(probability * 100, 0, 100)

    score = (
        ev_score * 0.30
        + prob_score * 0.18
        + gap_score * 0.15
        + matchup_score * 0.12
        + injury_score * 0.10
        + line_movement_score * 0.08
        + data_quality_score * 0.07
    )
    score = round(clamp(score, 0, 100), 1)

    if score >= 70 and ev > 0 and edge_margin > 0.015:
        recommendation = "BET"
    elif score >= 58 and ev > -0.015:
        recommendation = "LEAN"
    else:
        recommendation = "PASS"

    return {
        "edge_score": score,
        "confidence": round(score / 100, 4),
        "tier": confidence_tier(score),
        "risk": risk_tier(score, probability, ev),
        "recommendation": recommendation,
        "model_probability": round(probability, 4),
        "implied_probability": round(imp, 4),
        "edge_margin": round(edge_margin, 4),
        "edge": round(edge_margin, 4),
        "ev": round(ev, 4),
        "expected_value_per_1u": round(ev, 4),
        "fair_odds_decimal": round(1 / max(probability, 0.001), 3),
    }


def analyze_line_movement(
    open_line: float,
    current_line: float,
    open_odds: int,
    current_odds: int,
    public_bet_pct: float | None = None,
    money_pct: float | None = None,
) -> dict[str, Any]:
    line_delta = current_line - open_line
    odds_delta = current_odds - open_odds
    public_bet_pct = public_bet_pct if public_bet_pct is not None else 50
    money_pct = money_pct if money_pct is not None else 50
    steam = abs(line_delta) >= 1.0 or abs(odds_delta) >= 20
    reverse = abs(money_pct - public_bet_pct) >= 18 and money_pct > public_bet_pct
    score = 50 + clamp(abs(line_delta) * 12, 0, 20) + clamp(abs(odds_delta) * 0.5, 0, 18)
    if reverse:
        score += 8
    if steam:
        score += 7
    return {
        "open_line": open_line,
        "current_line": current_line,
        "line_delta": round(line_delta, 2),
        "open_odds": open_odds,
        "current_odds": current_odds,
        "odds_delta": odds_delta,
        "steam_detected": steam,
        "reverse_line_movement": reverse,
        "public_bet_pct": public_bet_pct,
        "money_pct": money_pct,
        "line_movement_score": round(clamp(score, 0, 100), 1),
        "note": "Steam/RLM signal found" if steam or reverse else "No major market move detected",
    }


def build_parlay(legs: list[dict[str, Any]], style: str = "balanced", target_legs: int | None = None) -> dict[str, Any]:
    clean = []
    for leg in legs:
        prob = float(leg.get("model_probability", leg.get("probability", 0.52)))
        odds = int(leg.get("odds", -110))
        clean.append({**leg, "model_probability": clamp(prob, 0.01, 0.99), "decimal_odds": american_to_decimal(odds)})

    if target_legs is not None:
        selected = sorted(clean, key=lambda x: x["model_probability"], reverse=True)[:max(1, int(target_legs))]
    elif style == "safe":
        selected = [x for x in clean if x["model_probability"] >= 0.57][:3]
    elif style == "lotto":
        selected = sorted(clean, key=lambda x: x["model_probability"], reverse=True)[:10]
    else:
        selected = [x for x in clean if x["model_probability"] >= 0.53][:6]

    if not selected:
        selected = sorted(clean, key=lambda x: x["model_probability"], reverse=True)[:2]

    combined_prob = prod([x["model_probability"] for x in selected]) if selected else 0
    combined_decimal = prod([x["decimal_odds"] for x in selected]) if selected else 0
    ev = combined_prob * (combined_decimal - 1) - (1 - combined_prob)

    subjects = [str(x.get("subject", x.get("player", ""))).lower() for x in selected]
    same_subject_count = len(subjects) - len(set(subjects))
    correlation_warning = same_subject_count > 0

    return {
        "style": style,
        "legs": selected,
        "leg_count": len(selected),
        "combined_probability": round(combined_prob, 4),
        "combined_decimal_odds": round(combined_decimal, 3),
        "expected_value_per_1u": round(ev, 4),
        "correlation_warning": correlation_warning,
        "warning": "Check same-player/team correlation before placing." if correlation_warning else "No obvious duplicate-subject correlation detected.",
    }


def analyze_betslip(legs: list[dict[str, Any]]) -> dict[str, Any]:
    graded = []
    for leg in legs:
        sim = simulate_hit_probability(
            projection=float(leg.get("projection", leg.get("line", 0))),
            line=float(leg.get("line", 0)),
            recent_values=[float(x) for x in leg.get("recent_values", [])],
            side=str(leg.get("side", "over")),
            market=str(leg.get("market", "")),
            runs=1600,
        )
        edge = build_edge_score(
            probability=sim["hit_probability"],
            odds=int(leg.get("odds", -110)),
            projection=sim["projection"],
            line=sim["line"],
            matchup_score=float(leg.get("matchup_score", 50)),
            injury_score=float(leg.get("injury_score", 50)),
            line_movement_score=float(leg.get("line_movement_score", 50)),
            data_quality_score=float(leg.get("data_quality_score", 55)),
        )
        graded.append({**leg, "simulation": sim, "edge": edge})

    weak = [x for x in graded if x["edge"]["recommendation"] == "PASS" or x["edge"]["edge_score"] < 58]
    strongest = sorted(graded, key=lambda x: x["edge"]["edge_score"], reverse=True)[:5]
    parlay = build_parlay([{**x, "model_probability": x["edge"]["model_probability"]} for x in graded], "balanced")

    return {
        "legs_reviewed": len(graded),
        "strongest_legs": strongest,
        "weak_legs": weak,
        "risk_flags": [f"Weak leg: {x.get('subject', x.get('player', 'unknown'))}" for x in weak],
        "balanced_parlay": parlay,
        "summary": f"{len(weak)} weak legs found. Best use: singles first, parlay only legs with positive EV.",
    }


def bankroll_plan(
    bankroll: float,
    edge_score: float,
    risk: str,
    max_daily_exposure_pct: float = 0.08,
) -> dict[str, Any]:
    if edge_score >= 85:
        unit_pct = 0.02
    elif edge_score >= 78:
        unit_pct = 0.015
    elif edge_score >= 70:
        unit_pct = 0.01
    elif edge_score >= 60:
        unit_pct = 0.005
    else:
        unit_pct = 0.0

    if "High" in risk:
        unit_pct *= 0.5

    stake = bankroll * unit_pct
    max_daily = bankroll * max_daily_exposure_pct
    return {
        "bankroll": round(bankroll, 2),
        "recommended_stake": round(stake, 2),
        "unit_pct": round(unit_pct, 4),
        "max_daily_exposure": round(max_daily, 2),
        "rule": "No chasing. Stop if daily exposure or stop-loss is reached.",
    }


def recap_learning(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    settled = [p for p in predictions if str(p.get("result", "")).lower() in ("win", "loss", "push")]
    wins = sum(1 for p in settled if str(p.get("result", "")).lower() == "win")
    losses = sum(1 for p in settled if str(p.get("result", "")).lower() == "loss")
    pushes = sum(1 for p in settled if str(p.get("result", "")).lower() == "push")
    graded = wins + losses
    win_rate = wins / graded if graded else 0

    misses = [p for p in settled if str(p.get("result", "")).lower() == "loss"]
    common_miss_tags: dict[str, int] = {}
    for miss in misses:
        for tag in miss.get("miss_tags", []):
            common_miss_tags[tag] = common_miss_tags.get(tag, 0) + 1

    adjustments = []
    if common_miss_tags.get("injury", 0) >= 2:
        adjustments.append("Raise injury/news penalty before locking props.")
    if common_miss_tags.get("minutes", 0) >= 2:
        adjustments.append("Lower confidence when minutes projection is unstable.")
    if common_miss_tags.get("blowout", 0) >= 2:
        adjustments.append("Add blowout-risk downgrade for favorites and high spreads.")
    if not adjustments:
        adjustments.append("No major formula adjustment found yet; keep collecting results.")

    return {
        "settled_count": len(settled),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": round(win_rate, 4),
        "common_miss_tags": common_miss_tags,
        "formula_adjustments": adjustments,
    }


def formula_snapshot() -> dict[str, Any]:
    return {
        "formula": [
            "Verify official lineup/injury context first",
            "Project role, minutes/volume, and usage",
            "Compare projection to sportsbook line",
            "Convert odds to implied probability",
            "Simulate hit probability",
            "Calculate EV and edge margin",
            "Apply matchup, injury, market movement, and data-quality weights",
            "Output BET / LEAN / PASS with tier and bankroll stake",
        ],
        "weights": {
            "ev_score": 0.30,
            "probability": 0.18,
            "projection_gap": 0.15,
            "matchup": 0.12,
            "injury": 0.10,
            "line_movement": 0.08,
            "data_quality": 0.07,
        },
    }
