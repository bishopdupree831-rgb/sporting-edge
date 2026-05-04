from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SPORT_FACTORS = {
    "NBA": {"pace": 1.08, "rotation": 0.09, "injury": 0.08, "weather": 0.0},
    "NFL": {"pace": 0.94, "rotation": 0.06, "injury": 0.1, "weather": 0.08},
    "MLB": {"pace": 0.72, "rotation": 0.04, "injury": 0.06, "weather": 0.09},
    "NHL": {"pace": 0.9, "rotation": 0.07, "injury": 0.08, "weather": 0.01},
    "MMA": {"pace": 0.62, "rotation": 0.03, "injury": 0.11, "weather": 0.0},
}


@dataclass(frozen=True)
class ContextScore:
    form: float
    matchup: float
    environment: float
    coaching: float
    injury: float

    @property
    def total(self) -> float:
        return round((self.form + self.matchup + self.environment + self.coaching - self.injury) / 4.0, 3)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def recent_form(values: list[float] | None, line: float = 0.0) -> float:
    if not values:
        return 0.58
    hit_rate = sum(1 for value in values if value >= line) / len(values) if line else 0.55
    trend = (values[-1] - values[0]) / max(abs(values[0]), 1)
    return clamp((hit_rate * 0.72) + (0.5 + trend * 0.18) * 0.28)


def matchup_score(sport: str, opponent_rank: float | None = None, rest_days: float | None = None) -> float:
    base = SPORT_FACTORS.get(sport.upper(), SPORT_FACTORS["NBA"])["pace"]
    rank_lift = 0.0 if opponent_rank is None else (15 - opponent_rank) / 60
    rest_lift = 0.0 if rest_days is None else min(rest_days, 4) * 0.018
    return clamp(0.48 + base * 0.18 + rank_lift + rest_lift)


def environment_score(sport: str, venue: str = "", weather: dict[str, Any] | None = None) -> float:
    sport = sport.upper()
    if sport in {"NBA", "NHL", "MMA"}:
        return 0.62
    weather = weather or {}
    wind = float(weather.get("wind_mph") or 0)
    temp = float(weather.get("temp_f") or 70)
    precipitation = float(weather.get("precip_probability") or 0)
    dome_bonus = 0.08 if "dome" in venue.lower() or "indoor" in venue.lower() else 0.0
    penalty = min(wind / 150, 0.1) + min(abs(temp - 70) / 300, 0.08) + min(precipitation / 500, 0.08)
    return clamp(0.62 + dome_bonus - penalty)


def coaching_score(tendency: str = "", market: str = "") -> float:
    text = f"{tendency} {market}".lower()
    lift = 0.0
    for token in ("pace", "pass", "volume", "aggressive", "power play", "usage"):
        if token in text:
            lift += 0.035
    for token in ("slow", "committee", "platoon", "minutes limit"):
        if token in text:
            lift -= 0.045
    return clamp(0.58 + lift)


def injury_risk(status: str = "", news: list[dict[str, Any]] | None = None) -> float:
    text = " ".join([status, *[str(item.get("headline", "")) for item in news or []]]).lower()
    risk = 0.04
    for token in ("questionable", "limited", "illness", "ankle", "hamstring", "lineup watch"):
        if token in text:
            risk += 0.05
    for token in ("out", "doubtful", "scratch"):
        if token in text:
            risk += 0.12
    return clamp(risk, 0.0, 0.45)


def context_score(payload: dict[str, Any]) -> ContextScore:
    sport = str(payload.get("sport") or "NBA").upper()
    line = float(payload.get("line") or 0)
    return ContextScore(
        form=recent_form(payload.get("recent"), line),
        matchup=matchup_score(sport, payload.get("opponent_rank"), payload.get("rest_days")),
        environment=environment_score(sport, payload.get("venue", ""), payload.get("weather")),
        coaching=coaching_score(payload.get("coaching", ""), payload.get("market", "")),
        injury=injury_risk(payload.get("status", ""), payload.get("news")),
    )
