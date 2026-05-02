from __future__ import annotations

import random
import statistics
import threading
import time
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="EdgeLab Sports Engine")
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

SIM_RUNS = 4000
EDGE_THRESHOLD = 0.05
POLL_INTERVAL = 15

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com/",
}

SAMPLE_PLAYERS = [
    {"name": "Jalen Brunson", "sport": "NBA", "minutes": 36.4, "usage": 0.31, "role": "primary", "market": "Points"},
    {"name": "Luka Doncic", "sport": "NBA", "minutes": 37.1, "usage": 0.34, "role": "primary", "market": "Points"},
    {"name": "Christian McCaffrey", "sport": "NFL", "minutes": 42.0, "usage": 0.30, "role": "primary", "market": "Rush+Rec Yards"},
    {"name": "CeeDee Lamb", "sport": "NFL", "minutes": 39.0, "usage": 0.28, "role": "primary", "market": "Receptions"},
    {"name": "Mookie Betts", "sport": "MLB", "minutes": 38.0, "usage": 0.27, "role": "primary", "market": "Total Bases"},
    {"name": "Bobby Witt Jr.", "sport": "MLB", "minutes": 37.5, "usage": 0.26, "role": "primary", "market": "Hits"},
    {"name": "Islam Makhachev", "sport": "MMA", "minutes": 25.0, "usage": 0.32, "role": "primary", "market": "Takedowns"},
    {"name": "Sean O'Malley", "sport": "MMA", "minutes": 25.0, "usage": 0.29, "role": "primary", "market": "Significant Strikes"},
]

SAMPLE_PROPS = {
    "Jalen Brunson": {"line": 27.5, "odds": -110, "market": "Points", "scale": 90},
    "Luka Doncic": {"line": 30.5, "odds": -110, "market": "Points", "scale": 92},
    "Christian McCaffrey": {"line": 112.5, "odds": -115, "market": "Rush+Rec Yards", "scale": 380},
    "CeeDee Lamb": {"line": 6.5, "odds": -105, "market": "Receptions", "scale": 24},
    "Mookie Betts": {"line": 1.5, "odds": -120, "market": "Total Bases", "scale": 7},
    "Bobby Witt Jr.": {"line": 1.5, "odds": +105, "market": "Hits", "scale": 5.8},
    "Islam Makhachev": {"line": 2.5, "odds": -125, "market": "Takedowns", "scale": 11},
    "Sean O'Malley": {"line": 74.5, "odds": -110, "market": "Significant Strikes", "scale": 270},
}

LATEST: dict[str, Any] = {
    "mode": "warming up",
    "top_bets": [],
    "all_bets": [],
    "parlay": [],
    "insights": [],
    "first_shot": {},
}


def fetch_nba_players() -> list[dict[str, Any]]:
    url = "https://stats.nba.com/stats/leaguedashplayerstats"
    params = {"Season": "2025-26", "PerMode": "PerGame"}

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        rows = data["resultSets"][0]["rowSet"][:12]
    except Exception:
        return []

    return [
        {
            "name": row[1],
            "sport": "NBA",
            "minutes": float(row[6] or 0),
            "usage": 0.22 + random.random() * 0.1,
            "role": "primary" if random.random() > 0.35 else "secondary",
            "market": "Points",
        }
        for row in rows
    ]


def fetch_players() -> list[dict[str, Any]]:
    live_nba = fetch_nba_players()
    names = {player["name"] for player in live_nba}
    return live_nba + [player for player in SAMPLE_PLAYERS if player["name"] not in names]


def fetch_props() -> dict[str, dict[str, Any]]:
    return SAMPLE_PROPS


def build_history(players: list[dict[str, Any]]) -> dict[str, float]:
    weights = {
        "primary": 0.22,
        "secondary": 0.14,
    }
    return {
        player["name"]: round(weights.get(player["role"], 0.09) + player["usage"] * 0.22, 3)
        for player in players[:12]
    }


def simulate_market(player: dict[str, Any], prop: dict[str, Any]) -> float:
    base = player["usage"] * prop["scale"] * max(0.55, player["minutes"] / 36)
    variance = max(base * 0.25, prop["line"] * 0.08)
    return max(0, random.gauss(base, variance))


def run_sim(player: dict[str, Any], prop: dict[str, Any]) -> list[float]:
    return [simulate_market(player, prop) for _ in range(SIM_RUNS)]


def hit_rate(results: list[float], line: float) -> float:
    return sum(1 for result in results if result > line) / len(results)


def odds_to_prob(odds: int) -> float:
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)


def analyze(player: dict[str, Any], prop: dict[str, Any]) -> dict[str, Any]:
    sim = run_sim(player, prop)
    hr = hit_rate(sim, prop["line"])
    implied = odds_to_prob(prop["odds"])
    edge = hr - implied
    confidence = hr * (1 - abs(edge))

    return {
        "edge": round(edge, 3),
        "hit_rate": round(hr, 3),
        "confidence": round(confidence, 3),
        "projection": round(statistics.mean(sim), 1),
        "bet": edge > EDGE_THRESHOLD and confidence > 0.52,
    }


def role_mult(role: str) -> float:
    return {"primary": 1.0, "secondary": 0.7}.get(role, 0.5)


def first_action(players: list[dict[str, Any]], history: dict[str, float]) -> dict[str, float]:
    candidates = [player for player in players if player["sport"] in {"NBA", "MMA"}][:10]
    weights = []

    for player in candidates:
        weight = (
            player["usage"] * 0.35
            + (player["minutes"] / 48) * 0.2
            + role_mult(player["role"]) * 0.15
            + history.get(player["name"], 0.1) * 0.3
        )
        weights.append(weight)

    total = sum(weights) or 1
    return {candidates[i]["name"]: round(weights[i] / total, 3) for i in range(len(candidates))}


def insights(players: list[dict[str, Any]]) -> list[str]:
    output = []
    for player in players:
        if player["usage"] > 0.28:
            output.append(f"{player['sport']}: {player['name']} usage spike")
        if player["minutes"] > 35:
            output.append(f"{player['sport']}: {player['name']} heavy workload")
    return output[:14]


def sharp_filter(bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [bet for bet in bets if bet["confidence"] > 0.55]


def build_parlay(bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = [bet for bet in bets if bet["edge"] > 0.06]
    return filtered[:3]


def engine_tick() -> dict[str, Any]:
    players = fetch_players()
    props = fetch_props()
    history = build_history(players)
    results = []

    for player in players:
        prop = props.get(player["name"])
        if not prop:
            continue
        analysis = analyze(player, prop)
        results.append(
            {
                "name": player["name"],
                "sport": player["sport"],
                "market": prop["market"],
                "line": prop["line"],
                "odds": prop["odds"],
                **analysis,
            }
        )

    ranked = sorted(results, key=lambda item: item["edge"], reverse=True)
    sharp = sharp_filter(ranked)

    return {
        "mode": "deployable sample engine",
        "top_bets": sharp[:10],
        "all_bets": ranked,
        "parlay": build_parlay(sharp),
        "insights": insights(players),
        "first_shot": first_action(players, history),
        "updated_at": int(time.time()),
    }


def loop() -> None:
    global LATEST
    while True:
        LATEST = engine_tick()
        time.sleep(POLL_INTERVAL)


@app.on_event("startup")
def startup() -> None:
    LATEST.update(engine_tick())
    threading.Thread(target=loop, daemon=True).start()


@app.get("/api")
def api() -> dict[str, Any]:
    return LATEST


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    html = (BASE_DIR / "index.html").read_text(encoding="utf-8")
    return html.replace('href="styles.css"', 'href="/static/styles.css"').replace('src="app.js"', 'src="/static/app.js"')
