from __future__ import annotations

import random
import statistics
import threading
import time
import os
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

TEAM_CATALOG = {
    "NFL": [
        "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills", "Carolina Panthers",
        "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns", "Dallas Cowboys", "Denver Broncos",
        "Detroit Lions", "Green Bay Packers", "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars",
        "Kansas City Chiefs", "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
        "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants", "New York Jets",
        "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers", "Seattle Seahawks",
        "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders",
    ],
    "MLB": [
        "Arizona Diamondbacks", "Athletics", "Atlanta Braves", "Baltimore Orioles", "Boston Red Sox",
        "Chicago Cubs", "Chicago White Sox", "Cincinnati Reds", "Cleveland Guardians", "Colorado Rockies",
        "Detroit Tigers", "Houston Astros", "Kansas City Royals", "Los Angeles Angels", "Los Angeles Dodgers",
        "Miami Marlins", "Milwaukee Brewers", "Minnesota Twins", "New York Mets", "New York Yankees",
        "Philadelphia Phillies", "Pittsburgh Pirates", "San Diego Padres", "San Francisco Giants",
        "Seattle Mariners", "St. Louis Cardinals", "Tampa Bay Rays", "Texas Rangers", "Toronto Blue Jays",
        "Washington Nationals",
    ],
    "NBA": [
        "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls",
        "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons", "Golden State Warriors",
        "Houston Rockets", "Indiana Pacers", "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies",
        "Miami Heat", "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
        "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers",
        "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz", "Washington Wizards",
    ],
    "MMA": [
        "UFC", "Bellator", "PFL", "ONE Championship", "Bantamweight", "Featherweight", "Lightweight",
        "Welterweight", "Middleweight", "Light Heavyweight", "Heavyweight",
    ],
}

MARKET_CATALOG = {
    "NFL": [
        "Passing Yards", "Passing Touchdowns", "Pass Attempts", "Completions", "Interceptions",
        "Rushing Yards", "Rush Attempts", "Receiving Yards", "Receptions", "Anytime Touchdown",
        "Kicking Points", "Sacks", "Tackles", "Team Total Points", "Spread", "Moneyline",
    ],
    "MLB": [
        "Hits", "Total Bases", "Runs", "RBIs", "Home Runs", "Stolen Bases", "Walks", "Strikeouts",
        "Pitcher Strikeouts", "Pitcher Outs", "Earned Runs", "Team Total Runs", "Moneyline", "Run Line",
    ],
    "NBA": [
        "Points", "Rebounds", "Assists", "Points+Rebounds+Assists", "Threes", "Steals", "Blocks",
        "Turnovers", "Double Double", "Team Total Points", "Spread", "Moneyline",
    ],
    "MMA": [
        "Moneyline", "Method Of Victory", "Fight Goes Distance", "Round Total", "Significant Strikes",
        "Takedowns", "Submission Attempts", "Knockdowns", "Control Time", "Win In Round",
    ],
}

SPORT_KEYS = {
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "NBA": "basketball_nba",
    "MMA": "mma_mixed_martial_arts",
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


class PredictionRequest(BaseModel):
    sport: str
    player: str | None = None
    team: str | None = None
    market: str
    line: float
    odds: int = -110


def stable_noise(*parts: Any, spread: float = 0.08) -> float:
    seed = "|".join(str(part).lower() for part in parts)
    value = sum(ord(char) for char in seed) % 1000
    return ((value / 1000) - 0.5) * spread


def market_scale(sport: str, market: str) -> tuple[float, float]:
    key = market.lower()
    if sport == "NFL":
        if "passing yards" in key:
            return 245, 38
        if "rushing yards" in key:
            return 58, 18
        if "receiving yards" in key:
            return 55, 20
        if "receptions" in key:
            return 4.8, 1.8
        if "touchdown" in key:
            return 0.42, 0.18
    if sport == "MLB":
        if "total bases" in key:
            return 1.65, 0.55
        if "hits" in key:
            return 1.05, 0.4
        if "strikeout" in key:
            return 5.4, 1.3
        if "home run" in key:
            return 0.22, 0.12
    if sport == "NBA":
        if "points" in key and "assists" not in key and "rebounds" not in key:
            return 22.5, 6
        if "rebounds" in key:
            return 6.5, 2.4
        if "assists" in key:
            return 5.4, 2
        if "threes" in key:
            return 2.2, 0.9
    if sport == "MMA":
        if "significant" in key:
            return 68, 24
        if "takedown" in key:
            return 2.1, 1.1
        if "round" in key:
            return 2.4, 0.7
        if "distance" in key:
            return 0.52, 0.16
    return 10, 3


def predict_market(request: PredictionRequest) -> dict[str, Any]:
    sport = request.sport.upper()
    market = request.market.strip()
    subject = request.player or request.team or "Unknown"
    baseline, volatility = market_scale(sport, market)
    matchup_lift = stable_noise(sport, subject, request.team, market, spread=0.18)
    projection = max(0, baseline * (1 + matchup_lift))
    simulated = [max(0, random.gauss(projection, volatility)) for _ in range(SIM_RUNS)]
    hr = hit_rate(simulated, request.line)
    implied = odds_to_prob(request.odds)
    edge = hr - implied
    confidence = hr * (1 - min(abs(edge), 0.35))

    if edge > 0.06 and confidence > 0.54:
        recommendation = "Play"
    elif edge < -0.06:
        recommendation = "Fade"
    else:
        recommendation = "Watch"

    return {
        "sport": sport,
        "subject": subject,
        "team": request.team,
        "market": market,
        "line": request.line,
        "odds": request.odds,
        "projection": round(statistics.mean(simulated), 2),
        "hit_rate": round(hr, 3),
        "implied_probability": round(implied, 3),
        "edge": round(edge, 3),
        "confidence": round(confidence, 3),
        "recommendation": recommendation,
        "explanation": (
            f"{subject} {market} is projected around {round(statistics.mean(simulated), 2)} against a "
            f"{request.line} line. The model compares simulated hit rate to implied odds probability."
        ),
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


def odds_api_key() -> str | None:
    return os.getenv("ODDS_API_KEY") or os.getenv("THE_ODDS_API_KEY")


def fetch_live_events(sport: str) -> list[dict[str, Any]]:
    key = odds_api_key()
    sport_key = SPORT_KEYS.get(sport.upper())
    if not key or not sport_key:
        return []

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events"
    try:
        response = requests.get(url, params={"apiKey": key}, timeout=8)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


def fetch_live_odds(sport: str) -> list[dict[str, Any]]:
    key = odds_api_key()
    sport_key = SPORT_KEYS.get(sport.upper())
    if not key or not sport_key:
        return []

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
    }
    try:
        response = requests.get(url, params=params, timeout=8)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


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


@app.get("/api/catalog")
def catalog() -> dict[str, Any]:
    return {
        "teams": TEAM_CATALOG,
        "markets": MARKET_CATALOG,
        "sample_players": SAMPLE_PLAYERS,
        "providers": {
            "odds_api_connected": bool(odds_api_key()),
            "odds_api_env_vars": ["ODDS_API_KEY", "THE_ODDS_API_KEY"],
        },
    }


@app.get("/api/events/{sport}")
def events(sport: str) -> dict[str, Any]:
    live_events = fetch_live_events(sport)
    return {
        "sport": sport.upper(),
        "source": "the-odds-api" if live_events else "catalog-fallback",
        "events": live_events,
        "teams": TEAM_CATALOG.get(sport.upper(), []),
    }


@app.get("/api/odds/{sport}")
def odds(sport: str) -> dict[str, Any]:
    live_odds = fetch_live_odds(sport)
    return {
        "sport": sport.upper(),
        "source": "the-odds-api" if live_odds else "sample-fallback",
        "odds": live_odds,
    }


@app.post("/api/predict")
def predict(request: PredictionRequest) -> dict[str, Any]:
    return predict_market(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    html = (BASE_DIR / "index.html").read_text(encoding="utf-8")
    return html.replace('href="styles.css"', 'href="/static/styles.css"').replace('src="app.js"', 'src="/static/app.js"')
