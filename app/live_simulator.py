from __future__ import annotations

import math
import random
import statistics
from datetime import datetime, timezone
from typing import Any

from app.providers import live_provider_connected, provider_statuses
from app.providers.odds_provider import fetch_live_odds, flatten_odds_events, odds_status
from app.providers.props_provider import fetch_props, props_status
from app.providers.stats_provider import fetch_live_games, fetch_player_stats, fetch_team_stats, stats_status
from app.services.odds_math import expected_value, implied_probability

SUPPORTED_SPORTS = {"NBA", "NFL", "MLB", "NHL", "MMA"}
MARKET_TYPES = {
    "moneyline", "spread", "total", "player_prop", "team_prop", "fighter_prop", "period_prop",
    "quarter_prop", "inning_prop", "first_basket", "first_scorer", "first_td", "first_hr",
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def numeric(context: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = context.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default


def list_average(value: Any, default: float = 0.0) -> float:
    if isinstance(value, list) and value:
        nums = []
        for item in value:
            try:
                nums.append(float(item))
            except (TypeError, ValueError):
                pass
        return statistics.fmean(nums) if nums else default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def provider_sources() -> list[dict[str, Any]]:
    return provider_statuses()


def provider_connected() -> bool:
    return live_provider_connected()


def unavailable_response(sport: str | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    message = "Live provider not connected. Real-time mode unavailable."
    return {
        "ok": False,
        "sport": sport,
        "provider_mode": "unavailable",
        "provider_message": message,
        "result_sentence": message,
        "trend_explanation": message,
        "data_freshness": now,
        "last_updated": now,
        "provider_sources": provider_sources(),
    }


def fetch_live_context(payload: dict[str, Any]) -> dict[str, Any]:
    sport = str(payload.get("sport") or "NBA").upper()
    context = dict(payload.get("live_context") or {})
    snapshots: dict[str, Any] = {}
    errors: list[str] = []

    if odds_status()["connected"]:
        try:
            odds = fetch_live_odds(sport=sport, include_player_props=True)
            snapshots["odds"] = odds
            rows = flatten_odds_events(odds.get("events", []))
            target_market = str(payload.get("stat_type") or payload.get("market_type") or "").lower()
            target_name = str(payload.get("player_name") or payload.get("team_name") or "").lower()
            for row in rows:
                row_text = f"{row.get('selection', '')} {row.get('market', '')}".lower()
                if (target_name and target_name in row_text) or (target_market and target_market in row_text):
                    if row.get("odds"):
                        payload["odds"] = row["odds"]
                        payload["sportsbook"] = payload.get("sportsbook") or row.get("sportsbook")
                    if row.get("point") is not None and not payload.get("line"):
                        payload["line"] = row["point"]
                    break
        except Exception as exc:
            errors.append(f"odds_provider: {exc}")

    if props_status()["connected"]:
        try:
            snapshots["props"] = fetch_props(sport=sport, market=payload.get("stat_type"))
        except Exception as exc:
            errors.append(f"props_provider: {exc}")

    if stats_status()["connected"]:
        try:
            snapshots["games"] = fetch_live_games(sport)
        except Exception as exc:
            errors.append(f"stats_games: {exc}")
        try:
            if payload.get("player_name"):
                snapshots["player_stats"] = fetch_player_stats(sport, search=payload["player_name"])
            if payload.get("team_name"):
                snapshots["team_stats"] = fetch_team_stats(sport, search=payload["team_name"])
        except Exception as exc:
            errors.append(f"stats_lookup: {exc}")

    # Provider data shapes vary by sport and plan. We only map numeric fields when
    # the provider returned them; otherwise user-entered live_context remains the source.
    context["_provider_snapshots"] = snapshots
    context["_provider_errors"] = errors
    context["_last_updated"] = datetime.now(timezone.utc).isoformat()
    payload["live_context"] = context
    return payload


def context_mean(payload: dict[str, Any]) -> float:
    context = payload.get("live_context") or {}
    line = float(payload.get("line") or 0)
    values = [
        numeric(context, "season_average", "season average", default=line) * 0.25,
        numeric(context, "last_5_average", "last 5 average", default=line) * 0.2,
        numeric(context, "last_10_average", "last 10 average", default=line) * 0.18,
        numeric(context, "opponent_average_allowed", "opponent average allowed", default=line) * 0.18,
        list_average(context.get("matchup_history") or context.get("matchup history"), line) * 0.09,
    ]
    base = sum(values) / 0.9 if values else line
    market = str(payload.get("market_type") or "").lower()
    if market == "moneyline":
        return clamp(base or 0.54, 0.05, 0.95)
    return max(0.01, base)


def adjustment_multiplier(payload: dict[str, Any]) -> float:
    sport = str(payload.get("sport") or "").upper()
    context = payload.get("live_context") or {}
    usage = numeric(context, "usage_rate", "usage rate", default=0)
    minutes = numeric(context, "minutes_or_snap_count_projection", "minutes", "snap_count_projection", default=0)
    adjustments = [
        numeric(context, "injury_adjustment", "injury adjustment"),
        numeric(context, "lineup_adjustment", "lineup adjustment"),
        numeric(context, "pace_adjustment", "pace adjustment"),
        numeric(context, "odds_movement", "odds movement") / 10,
    ]
    if sport in {"NFL", "MLB"}:
        adjustments.append(numeric(context, "weather_adjustment", "weather adjustment"))
    if sport == "MLB":
        adjustments.append(numeric(context, "pitcher_adjustment", "pitcher adjustment"))
    if sport == "NHL":
        adjustments.append(numeric(context, "goalie_adjustment", "goalie adjustment"))
    if sport == "MMA":
        adjustments.append(numeric(context, "fight_style_adjustment", "fight style adjustment"))
    if usage:
        adjustments.append((usage - 0.2) * 0.12 if usage <= 1 else (usage - 20) / 500)
    if minutes:
        adjustments.append(min(minutes, 60) / 1800)
    public = numeric(context, "public_betting_percentage", "public betting percentage", default=50)
    sharp = str(context.get("sharp_money_signal") or context.get("sharp money signal") or "").lower()
    if "yes" in sharp or "true" in sharp or "sharp" in sharp:
        adjustments.append(0.035)
    if public >= 70 and not sharp:
        adjustments.append(-0.015)
    return clamp(1 + sum(adjustments), 0.35, 1.85)


def market_sigma(sport: str, market_type: str, mean: float) -> float:
    base = {
        "NBA": 0.22,
        "NFL": 0.28,
        "MLB": 0.42,
        "NHL": 0.36,
        "MMA": 0.48,
    }.get(sport, 0.3)
    if market_type in {"first_basket", "first_scorer", "first_td", "first_hr", "moneyline"}:
        return 0.5
    if market_type in {"spread", "total"}:
        base *= 0.75
    return max(0.35, abs(mean) * base)


def percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    index = int(round((len(sorted_values) - 1) * pct))
    return sorted_values[index]


def confidence_grade(hit_rate: float, edge: float, simulations: int) -> str:
    stability = min(1.0, math.log10(max(simulations, 10)) / 5)
    score = hit_rate * 0.72 + max(edge, 0) * 0.8 + stability * 0.08
    if score >= 0.72:
        return "A"
    if score >= 0.64:
        return "B"
    if score >= 0.56:
        return "C"
    return "D"


def verdict(edge: float, hit_rate: float) -> str:
    if edge >= 0.08 and hit_rate >= 0.57:
        return "Strong research candidate"
    if edge >= 0.04:
        return "Playable lean"
    if edge >= 0:
        return "Thin edge, compare books"
    return "Pass or wait for a better line"


def simulate(payload: dict[str, Any]) -> dict[str, Any]:
    sport = str(payload.get("sport") or "").upper()
    if sport not in SUPPORTED_SPORTS:
        raise ValueError("sport must be one of NBA, NFL, MLB, NHL, MMA")
    connected = provider_connected()
    provider_unavailable_message = ""
    if connected:
        payload = fetch_live_context(payload)
    else:
        context = dict(payload.get("live_context") or {})
        context["_last_updated"] = datetime.now(timezone.utc).isoformat()
        payload["live_context"] = context
        provider_unavailable_message = "Live provider not connected. Using manual mode."
    market_type = str(payload.get("market_type") or "player_prop").lower().replace(" ", "_").replace("/", "_")
    if market_type not in MARKET_TYPES:
        market_type = "player_prop"
    simulations = int(payload.get("simulations") or 10000)
    simulations = max(1000, min(simulations, 100000))
    line = float(payload.get("line") or 0)
    odds = int(payload.get("odds") or -110)
    mean = context_mean(payload) * adjustment_multiplier(payload)
    sigma = market_sigma(sport, market_type, mean)
    rng = random.Random(f"{sport}|{payload.get('matchup')}|{payload.get('player_name')}|{payload.get('team_name')}|{payload.get('stat_type')}|{line}|{odds}|{simulations}")

    values: list[float] = []
    hits = 0
    for _ in range(simulations):
        if market_type in {"moneyline", "first_basket", "first_scorer", "first_td", "first_hr"}:
            probability = clamp(mean if mean <= 1 else mean / 100, 0.02, 0.98)
            result = 1.0 if rng.random() < probability else 0.0
            hit = result >= 1
        else:
            result = max(0.0, rng.gauss(mean, sigma))
            hit = result > line
        values.append(result)
        if hit:
            hits += 1

    values.sort()
    hit_rate = hits / simulations
    miss_rate = 1 - hit_rate
    implied = implied_probability(odds)
    edge = hit_rate - implied
    ev = expected_value(hit_rate, odds)
    target_name = payload.get("player_name") or payload.get("team_name") or payload.get("matchup") or "This market"
    stat = payload.get("stat_type") or payload.get("market_type") or "market"
    phrase = f"{target_name} over {line:g} {stat} hit {hits:,} out of {simulations:,} simulations, or {hit_rate * 100:.1f}% of the time."
    provider_message = provider_unavailable_message
    provider_errors = (payload.get("live_context") or {}).get("_provider_errors") or []
    provider_snapshots = (payload.get("live_context") or {}).get("_provider_snapshots") or {}
    if provider_errors and not provider_snapshots:
        provider_message = "; ".join(provider_errors)
    elif any((snapshot.get("meta") or {}).get("cache_status") for snapshot in provider_snapshots.values() if isinstance(snapshot, dict)):
        provider_message = "Using cached data due to API limits"
    return {
        "ok": True,
        "sport": sport,
        "matchup": payload.get("matchup"),
        "market_type": market_type,
        "player_name": payload.get("player_name"),
        "team_name": payload.get("team_name"),
        "stat_type": payload.get("stat_type"),
        "line": line,
        "odds": odds,
        "sportsbook": payload.get("sportsbook"),
        "simulations": simulations,
        "hits": hits,
        "misses": simulations - hits,
        "hit_percentage": round(hit_rate, 4),
        "miss_percentage": round(miss_rate, 4),
        "average_result": round(statistics.fmean(values), 3),
        "median_result": round(statistics.median(values), 3),
        "percentile_25": round(percentile(values, 0.25), 3),
        "percentile_75": round(percentile(values, 0.75), 3),
        "implied_probability": round(implied, 4),
        "model_edge": round(edge, 4),
        "expected_value": round(ev, 4),
        "confidence_grade": confidence_grade(hit_rate, edge, simulations),
        "betting_verdict": verdict(edge, hit_rate),
        "result_sentence": phrase.replace(" hit ", " hit "),
        "trend_explanation": "Model blends manual/live context averages with usage, lineup, injury, pace, environment, market movement, public percentage, and sharp-signal adjustments.",
        "data_freshness": datetime.now(timezone.utc).isoformat(),
        "last_updated": (payload.get("live_context") or {}).get("_last_updated") or datetime.now(timezone.utc).isoformat(),
        "provider_sources": provider_sources(),
        "provider_mode": "live-provider-enriched" if connected else "manual-input",
        "provider_message": provider_message,
        "provider_snapshots": provider_snapshots,
    }
