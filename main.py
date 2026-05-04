from __future__ import annotations

import random
import statistics
import threading
import time
import os
import json
import hashlib
import secrets
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from app.routes.betslip import router as betslip_router
from app.routes.community import router as community_router
from app.routes.intelligence import router as intelligence_router
from app.routes.live_simulator import router as live_simulator_router
from app.routes.markets import router as markets_router
from app.routes.parlay_workbench import router as parlay_workbench_router
from app.routes.sharp_terminal import router as sharp_terminal_router
from app.routes.simulator import router as simulator_router
from odds_parlay_routes import router as odds_parlay_router

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_DEFAULT = Path("/tmp/edgelab.db") if os.getenv("RENDER") else BASE_DIR / "edgelab.db"
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", SQLITE_DEFAULT))

try:
    import psycopg
except Exception:  # psycopg is optional locally; Render can install it for Postgres.
    psycopg = None

app = FastAPI(title="EdgeLab Sports Engine")
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")
app.include_router(simulator_router)
app.include_router(parlay_workbench_router)
app.include_router(intelligence_router)
app.include_router(odds_parlay_router)
app.include_router(live_simulator_router)
app.include_router(sharp_terminal_router)
app.include_router(community_router)
app.include_router(markets_router)
app.include_router(betslip_router)

SIM_RUNS = 4000
EDGE_THRESHOLD = 0.05
POLL_INTERVAL = 300
DAILY_REFRESH_INTERVAL = 86400
HTTP_TIMEOUT = 10
CACHE_TTL = 900

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
    "NHL": [
        "Anaheim Ducks", "Boston Bruins", "Buffalo Sabres", "Calgary Flames", "Carolina Hurricanes",
        "Chicago Blackhawks", "Colorado Avalanche", "Columbus Blue Jackets", "Dallas Stars", "Detroit Red Wings",
        "Edmonton Oilers", "Florida Panthers", "Los Angeles Kings", "Minnesota Wild", "Montreal Canadiens",
        "Nashville Predators", "New Jersey Devils", "New York Islanders", "New York Rangers", "Ottawa Senators",
        "Philadelphia Flyers", "Pittsburgh Penguins", "San Jose Sharks", "Seattle Kraken", "St. Louis Blues",
        "Tampa Bay Lightning", "Toronto Maple Leafs", "Utah Mammoth", "Vancouver Canucks", "Vegas Golden Knights",
        "Washington Capitals", "Winnipeg Jets",
    ],
    "MMA": [
        "UFC", "Bellator", "PFL", "ONE Championship", "Bantamweight", "Featherweight", "Lightweight",
        "Welterweight", "Middleweight", "Light Heavyweight", "Heavyweight",
    ],
}

SUPPORTED_SPORTS = ["NFL", "MLB", "NBA", "NHL", "MMA"]
LAST_DAILY_REFRESH: dict[str, Any] = {"timestamp": None, "status": "not run", "sports": []}

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
    "NHL": [
        "Shots On Goal", "Points", "Assists", "Goals", "Saves", "Goals Against", "Power Play Points",
        "Blocked Shots", "Team Total Goals", "Puck Line", "Moneyline", "Total Goals",
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
    "NHL": "icehockey_nhl",
    "MMA": "mma_mixed_martial_arts",
}

SPORTSDATA_LEAGUES = {
    "NFL": "nfl",
    "MLB": "mlb",
    "NBA": "nba",
    "NHL": "nhl",
}

SPORTSDATA_STAT_FIELDS = {
    "NFL": {
        "passing yards": ["PassingYards"],
        "passing touchdowns": ["PassingTouchdowns"],
        "pass attempts": ["PassingAttempts"],
        "completions": ["PassingCompletions", "Completions"],
        "interceptions": ["PassingInterceptions", "Interceptions"],
        "rushing yards": ["RushingYards"],
        "rush attempts": ["RushingAttempts"],
        "receiving yards": ["ReceivingYards"],
        "receptions": ["Receptions"],
        "sacks": ["Sacks"],
        "tackles": ["Tackles"],
    },
    "MLB": {
        "hits": ["Hits"],
        "total bases": ["TotalBases"],
        "runs": ["Runs"],
        "rbis": ["RunsBattedIn", "RBIs"],
        "home runs": ["HomeRuns"],
        "stolen bases": ["StolenBases"],
        "walks": ["Walks"],
        "strikeouts": ["Strikeouts"],
        "pitcher strikeouts": ["PitchingStrikeouts", "Strikeouts"],
        "pitcher outs": ["Outs", "InningsPitchedDecimal"],
        "earned runs": ["EarnedRuns"],
    },
    "NBA": {
        "points": ["Points"],
        "rebounds": ["Rebounds"],
        "assists": ["Assists"],
        "points+rebounds+assists": ["Points", "Rebounds", "Assists"],
        "threes": ["ThreePointersMade", "ThreePointers"],
        "steals": ["Steals"],
        "blocks": ["BlockedShots", "Blocks"],
        "turnovers": ["Turnovers"],
    },
    "NHL": {
        "shots on goal": ["ShotsOnGoal", "Shots"],
        "points": ["Points"],
        "assists": ["Assists"],
        "goals": ["Goals"],
        "saves": ["Saves"],
        "goals against": ["GoalsAgainst"],
        "power play points": ["PowerPlayPoints"],
        "blocked shots": ["BlockedShots"],
    },
}

CACHE: dict[str, tuple[float, Any]] = {}
PREDICTION_LOG: list[dict[str, Any]] = []
DB_READY = False

MARKET_SOURCE_STACK = [
    {"name": "Dimers / Sports-AI style", "role": "true_probability", "use": "Compare model probability against book implied probability."},
    {"name": "OddsTrader / BettingPros style", "role": "best_lines", "use": "Find the best available price and line across books."},
    {"name": "Action Network style", "role": "sharp_money", "use": "Track bet percentage, money percentage, and reverse line movement."},
    {"name": "Covers / VSiN style", "role": "trends", "use": "Add situational systems, ATS trends, rest, travel, pace, and matchup context."},
    {"name": "Pickswise / SportyTrader style", "role": "explanation", "use": "Create simple summaries for quick user decisions."},
    {"name": "Polymarket style", "role": "crowd_probability", "use": "Compare market sentiment against sportsbook implied odds."},
]

ENVIRONMENT_PROFILES = {
    "NFL": {
        "Arizona Cardinals": {"venue": "State Farm Stadium", "surface": "grass", "roof": "retractable", "weather": "low"},
        "Atlanta Falcons": {"venue": "Mercedes-Benz Stadium", "surface": "turf", "roof": "dome", "weather": "low"},
        "Buffalo Bills": {"venue": "Highmark Stadium", "surface": "turf", "roof": "outdoor", "weather": "high"},
        "Chicago Bears": {"venue": "Soldier Field", "surface": "grass", "roof": "outdoor", "weather": "high"},
        "Dallas Cowboys": {"venue": "AT&T Stadium", "surface": "turf", "roof": "retractable", "weather": "low"},
        "Denver Broncos": {"venue": "Empower Field", "surface": "grass", "roof": "outdoor", "weather": "medium"},
        "Detroit Lions": {"venue": "Ford Field", "surface": "turf", "roof": "dome", "weather": "low"},
        "Green Bay Packers": {"venue": "Lambeau Field", "surface": "grass", "roof": "outdoor", "weather": "high"},
        "Houston Texans": {"venue": "NRG Stadium", "surface": "turf", "roof": "retractable", "weather": "low"},
        "Indianapolis Colts": {"venue": "Lucas Oil Stadium", "surface": "turf", "roof": "retractable", "weather": "low"},
        "Las Vegas Raiders": {"venue": "Allegiant Stadium", "surface": "grass", "roof": "dome", "weather": "low"},
        "Los Angeles Rams": {"venue": "SoFi Stadium", "surface": "turf", "roof": "canopy", "weather": "low"},
        "Miami Dolphins": {"venue": "Hard Rock Stadium", "surface": "grass", "roof": "outdoor", "weather": "medium"},
        "Minnesota Vikings": {"venue": "U.S. Bank Stadium", "surface": "turf", "roof": "dome", "weather": "low"},
        "New Orleans Saints": {"venue": "Caesars Superdome", "surface": "turf", "roof": "dome", "weather": "low"},
        "New York Giants": {"venue": "MetLife Stadium", "surface": "turf", "roof": "outdoor", "weather": "high"},
        "New York Jets": {"venue": "MetLife Stadium", "surface": "turf", "roof": "outdoor", "weather": "high"},
        "Philadelphia Eagles": {"venue": "Lincoln Financial Field", "surface": "grass", "roof": "outdoor", "weather": "medium"},
        "Pittsburgh Steelers": {"venue": "Acrisure Stadium", "surface": "grass", "roof": "outdoor", "weather": "high"},
        "Seattle Seahawks": {"venue": "Lumen Field", "surface": "turf", "roof": "outdoor", "weather": "medium"},
    },
    "MLB": {
        "Arizona Diamondbacks": {"venue": "Chase Field", "surface": "turf", "roof": "retractable", "weather": "low"},
        "Boston Red Sox": {"venue": "Fenway Park", "surface": "grass", "roof": "outdoor", "weather": "medium"},
        "Chicago Cubs": {"venue": "Wrigley Field", "surface": "grass", "roof": "outdoor", "weather": "high"},
        "Houston Astros": {"venue": "Daikin Park", "surface": "grass", "roof": "retractable", "weather": "low"},
        "Los Angeles Dodgers": {"venue": "Dodger Stadium", "surface": "grass", "roof": "outdoor", "weather": "low"},
        "Miami Marlins": {"venue": "loanDepot park", "surface": "turf", "roof": "retractable", "weather": "low"},
        "Milwaukee Brewers": {"venue": "American Family Field", "surface": "grass", "roof": "retractable", "weather": "low"},
        "New York Yankees": {"venue": "Yankee Stadium", "surface": "grass", "roof": "outdoor", "weather": "medium"},
        "San Francisco Giants": {"venue": "Oracle Park", "surface": "grass", "roof": "outdoor", "weather": "high"},
        "Seattle Mariners": {"venue": "T-Mobile Park", "surface": "grass", "roof": "retractable", "weather": "low"},
        "Tampa Bay Rays": {"venue": "Tropicana Field", "surface": "turf", "roof": "dome", "weather": "low"},
        "Toronto Blue Jays": {"venue": "Rogers Centre", "surface": "turf", "roof": "retractable", "weather": "low"},
    },
    "NHL": {
        "default": {"venue": "indoor arena", "surface": "ice", "roof": "indoor", "weather": "low"},
    },
    "NBA": {
        "default": {"venue": "indoor arena", "surface": "court", "roof": "indoor", "weather": "low"},
    },
    "MMA": {
        "default": {"venue": "indoor arena", "surface": "mat/cage", "roof": "indoor", "weather": "low"},
    },
}

DATA_REFRESH_POLICY = {
    "live_odds": {"ttl_seconds": 900, "reason": "Odds move often, but API quotas need protection."},
    "events": {"ttl_seconds": 900, "reason": "Matchups update during schedule changes."},
    "player_stats": {"ttl_seconds": 1800, "reason": "Game logs and rosters change after games and injury updates."},
    "news_injuries": {"ttl_seconds": 600, "reason": "Late scratches and lineup notes matter quickly."},
    "environment": {"ttl_seconds": 1800, "reason": "Weather, roof, turf, and venue context should refresh before games."},
}


def weather_api_key() -> str:
    return os.getenv("WEATHER_API_KEY") or os.getenv("OPENWEATHER_API_KEY") or ""


def weather_context(sport: str, team: str = "") -> dict[str, Any]:
    profile = find_environment_profile(sport.upper(), team)
    if profile.get("roof") in {"dome", "indoor"}:
        return {
            "source": "environment-profile",
            "impact": "low",
            "summary": "Indoor or dome environment keeps direct weather impact low.",
            "profile": profile,
        }
    key = weather_api_key()
    if not key:
        return {
            "source": "modeled-weather",
            "impact": profile.get("weather", "unknown"),
            "summary": "Connect WEATHER_API_KEY or OPENWEATHER_API_KEY for live wind, rain, and temperature.",
            "profile": profile,
        }
    query = team or profile.get("venue") or ""
    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": query, "appid": key, "units": "imperial"},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        wind = data.get("wind", {}).get("speed")
        temp = data.get("main", {}).get("temp")
        weather = ", ".join(item.get("description", "") for item in data.get("weather", []))
        impact = "high" if (wind or 0) >= 15 else "medium" if (wind or 0) >= 10 else "low"
        return {
            "source": "openweather",
            "impact": impact,
            "summary": f"{weather or 'Weather loaded'}; temp {temp}; wind {wind} mph.",
            "profile": profile,
            "raw": {"temp": temp, "wind": wind, "weather": weather},
        }
    except Exception:
        return {
            "source": "weather-fallback",
            "impact": profile.get("weather", "unknown"),
            "summary": "Weather provider did not return data; using venue profile.",
            "profile": profile,
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


class AskRequest(BaseModel):
    question: str
    sport: str = "All"


class OutcomeRequest(BaseModel):
    outcome: str


class UserAuthRequest(BaseModel):
    username: str
    password: str


class WatchlistRequest(BaseModel):
    token: str | None = None
    subject: str
    sport: str
    market: str
    line: float
    odds: int = -110
    threshold: float = 0.6


class SavedCardRequest(BaseModel):
    token: str | None = None
    name: str = "Saved card"
    legs: list[dict[str, Any]]


class AlertRequest(BaseModel):
    token: str | None = None
    subject: str
    sport: str
    market: str
    threshold: float = 0.6


def postgres_enabled() -> bool:
    return bool(DATABASE_URL) and psycopg is not None and urlparse(DATABASE_URL).scheme.startswith("postgres")


def db_connect() -> Any:
    if postgres_enabled():
        return psycopg.connect(DATABASE_URL)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_execute(query: str, params: tuple[Any, ...] = ()) -> None:
    if postgres_enabled():
        query = query.replace("?", "%s")
    with db_connect() as conn:
        conn.execute(query, params)
        conn.commit()


def db_fetchall(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    if postgres_enabled():
        query = query.replace("?", "%s")
    with db_connect() as conn:
        cur = conn.execute(query, params)
        rows = cur.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], sqlite3.Row):
            return [dict(row) for row in rows]
        columns = [col.name if hasattr(col, "name") else col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in rows]


def db_fetchone(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    rows = db_fetchall(query, params)
    return rows[0] if rows else None


def init_db() -> None:
    global DB_READY
    statements = [
        """CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS predictions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            timestamp INTEGER NOT NULL,
            sport TEXT,
            subject TEXT,
            market TEXT,
            line REAL,
            odds INTEGER,
            projection REAL,
            recommendation TEXT,
            confidence REAL,
            edge REAL,
            risk_json TEXT,
            source TEXT,
            outcome TEXT,
            closing_line REAL,
            closing_odds INTEGER,
            clv REAL,
            data_json TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS watchlist (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            subject TEXT,
            sport TEXT,
            market TEXT,
            line REAL,
            odds INTEGER,
            threshold REAL,
            created_at INTEGER NOT NULL,
            last_signal TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS saved_cards (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            legs_json TEXT,
            created_at INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            subject TEXT,
            sport TEXT,
            market TEXT,
            threshold REAL,
            status TEXT,
            created_at INTEGER NOT NULL,
            last_checked INTEGER,
            last_message TEXT
        )""",
    ]
    for statement in statements:
        db_execute(statement)
    DB_READY = True


def json_load(value: Any, fallback: Any = None) -> Any:
    if value in (None, ""):
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def user_from_token(token: str | None) -> dict[str, Any] | None:
    if not token or not DB_READY:
        return None
    row = db_fetchone(
        "SELECT users.id, users.username FROM sessions JOIN users ON sessions.user_id = users.id WHERE sessions.token = ?",
        (token,),
    )
    return row


def current_season(sport: str) -> int:
    # Sports seasons cross calendar years; these defaults keep current-year deployments usable.
    if sport.upper() in {"NFL", "NBA"}:
        return 2025
    return 2026


def cache_get(key: str) -> Any | None:
    item = CACHE.get(key)
    if not item:
        return None
    timestamp, value = item
    if time.time() - timestamp > CACHE_TTL:
        CACHE.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any) -> Any:
    CACHE[key] = (time.time(), value)
    return value


def sportsdata_key() -> str | None:
    return os.getenv("SPORTSDATA_API_KEY") or os.getenv("SPORTS_DATA_API_KEY")


def sportsdata_get(path: str) -> Any | None:
    key = sportsdata_key()
    if not key:
        return None

    cached = cache_get(path)
    if cached is not None:
        return cached

    url = f"https://api.sportsdata.io{path}"
    headers = {"Ocp-Apim-Subscription-Key": key}
    try:
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return cache_set(path, response.json())
    except Exception:
        return None


def sportsdata_candidates(sport: str, feed: str, *parts: Any) -> list[str]:
    league = SPORTSDATA_LEAGUES.get(sport.upper())
    if not league:
        return []
    suffix = "/".join(str(part) for part in parts if part is not None)
    suffix = f"/{suffix}" if suffix else ""

    if feed == "players":
        return [
            f"/v3/{league}/scores/json/Players",
            f"/v3/{league}/scores/json/PlayersBasic",
        ]
    if feed == "teams":
        return [f"/v3/{league}/scores/json/Teams"]
    if feed == "player_game_logs":
        return [
            f"/v3/{league}/stats/json/PlayerGameStatsByPlayer{suffix}",
            f"/v3/{league}/stats/json/PlayerGameLogsByPlayer{suffix}",
            f"/v3/{league}/stats/json/PlayerGameStatsBySeason{suffix}",
        ]
    if feed == "player_season_stats":
        return [
            f"/v3/{league}/stats/json/PlayerSeasonStats{suffix}",
            f"/v3/{league}/stats/json/PlayerSeasonStatsByPlayer{suffix}",
        ]
    if feed == "injuries":
        return [
            f"/v3/{league}/scores/json/Injuries",
            f"/v3/{league}/scores/json/PlayersByInjured",
        ]
    if feed == "news":
        return [
            f"/v3/{league}/news/json/News",
            f"/v3/{league}/news/json/NewsByDate{suffix}",
            f"/v3/{league}/news/json/PlayerNews",
        ]
    return []


def sportsdata_first(sport: str, feed: str, *parts: Any) -> tuple[Any | None, str | None]:
    for path in sportsdata_candidates(sport, feed, *parts):
        data = sportsdata_get(path)
        if data:
            return data, path
    return None, None


def normalize_name(player: dict[str, Any]) -> str:
    if player.get("Name"):
        return str(player["Name"])
    first = player.get("FirstName") or ""
    last = player.get("LastName") or ""
    return f"{first} {last}".strip()


def find_sportsdata_player(sport: str, query: str) -> dict[str, Any] | None:
    players, _ = sportsdata_first(sport, "players")
    if not isinstance(players, list) or not query:
        return None

    lowered = query.lower().strip()
    exact = [player for player in players if normalize_name(player).lower() == lowered]
    if exact:
        return exact[0]
    partial = [player for player in players if lowered in normalize_name(player).lower()]
    return partial[0] if partial else None


def sportsdata_player_id(player: dict[str, Any]) -> Any | None:
    return player.get("PlayerID") or player.get("PlayerId") or player.get("GlobalPlayerID")


def stat_values_from_rows(rows: list[dict[str, Any]], sport: str, market: str) -> list[float]:
    market_key = market.lower().strip()
    fields = SPORTSDATA_STAT_FIELDS.get(sport.upper(), {}).get(market_key)
    if not fields:
        for known_market, known_fields in SPORTSDATA_STAT_FIELDS.get(sport.upper(), {}).items():
            if known_market in market_key or market_key in known_market:
                fields = known_fields
                break
    if not fields:
        return []

    values = []
    for row in rows:
        total = 0.0
        found = False
        for field in fields:
            value = row.get(field)
            if isinstance(value, (int, float)):
                total += float(value)
                found = True
        if found:
            values.append(total)
    return values


def fetch_recent_player_values(sport: str, player_id: Any, market: str) -> tuple[list[float], str | None]:
    season = current_season(sport)
    candidates = []
    if sport.upper() == "NFL":
        candidates.append((season, player_id))
    else:
        candidates.append((season, player_id))

    for parts in candidates:
        data, path = sportsdata_first(sport, "player_game_logs", *parts)
        if isinstance(data, list):
            values = stat_values_from_rows(data, sport, market)
            if values:
                return values[-12:], path

    season_data, path = sportsdata_first(sport, "player_season_stats", season)
    if isinstance(season_data, list):
        row = next((item for item in season_data if sportsdata_player_id(item) == player_id), None)
        if row:
            values = stat_values_from_rows([row], sport, market)
            games = row.get("Games") or row.get("Started") or row.get("Played") or 1
            if values and isinstance(games, (int, float)) and games:
                return [values[0] / float(games)], path

    return [], None


def injury_note(sport: str, player_id: Any) -> str | None:
    injuries, _ = sportsdata_first(sport, "injuries")
    if not isinstance(injuries, list):
        return None
    for item in injuries:
        if sportsdata_player_id(item) == player_id:
            status = item.get("InjuryStatus") or item.get("Status") or item.get("GameStatus")
            body_part = item.get("BodyPart") or item.get("InjuryBodyPart")
            if status or body_part:
                return " / ".join(str(part) for part in [status, body_part] if part)
    return None


def fetch_sports_context(sport: str, query: str = "") -> dict[str, Any]:
    sport = sport.upper()
    lowered = query.lower().strip()
    injuries, injury_path = sportsdata_first(sport, "injuries")
    news, news_path = sportsdata_first(sport, "news")

    injury_rows = []
    if isinstance(injuries, list):
        for item in injuries:
            text = " ".join(str(item.get(key, "")) for key in [
                "Name", "PlayerName", "FirstName", "LastName", "Team", "InjuryStatus", "Status", "BodyPart",
                "InjuryBodyPart", "Updated", "Practice"
            ])
            if not lowered or lowered in text.lower():
                injury_rows.append({
                    "player": item.get("Name") or item.get("PlayerName") or " ".join(str(item.get(k, "")) for k in ["FirstName", "LastName"]).strip(),
                    "team": item.get("Team"),
                    "status": item.get("InjuryStatus") or item.get("Status") or item.get("GameStatus"),
                    "body_part": item.get("BodyPart") or item.get("InjuryBodyPart"),
                    "updated": item.get("Updated") or item.get("UpdatedDate"),
                    "source": "sportsdataio-injuries",
                })
            if len(injury_rows) >= 25:
                break

    news_rows = []
    if isinstance(news, list):
        for item in news:
            text = " ".join(str(item.get(key, "")) for key in [
                "Title", "Content", "TermsOfUse", "PlayerName", "Team", "Source", "TimeAgo"
            ])
            if not lowered or lowered in text.lower():
                news_rows.append({
                    "title": item.get("Title"),
                    "player": item.get("PlayerName"),
                    "team": item.get("Team"),
                    "source": item.get("Source") or "sportsdataio-news",
                    "time_ago": item.get("TimeAgo"),
                    "updated": item.get("Updated") or item.get("Published"),
                    "summary": item.get("Content") or item.get("Title"),
                })
            if len(news_rows) >= 25:
                break

    return {
        "sport": sport,
        "query": query,
        "sources": {
            "injuries": injury_path,
            "news": news_path,
            "sportsdata_api_connected": bool(sportsdata_key()),
        },
        "injuries": injury_rows,
        "news": news_rows,
    }


def context_warnings(sport: str, query: str) -> list[str]:
    context = fetch_sports_context(sport, query)
    warnings = []
    for injury in context["injuries"][:3]:
        detail = " / ".join(str(part) for part in [injury.get("player"), injury.get("team"), injury.get("status"), injury.get("body_part")] if part)
        if detail:
            warnings.append(f"Injury wire: {detail}.")
    for item in context["news"][:2]:
        title = item.get("title") or item.get("summary")
        if title:
            warnings.append(f"News wire: {title}.")
    return warnings


def stats_based_prediction(request: PredictionRequest) -> dict[str, Any] | None:
    sport = request.sport.upper()
    if sport not in SPORTSDATA_LEAGUES or not request.player:
        return None

    player = find_sportsdata_player(sport, request.player)
    if not player:
        return None

    player_id = sportsdata_player_id(player)
    if not player_id:
        return None

    values, feed_path = fetch_recent_player_values(sport, player_id, request.market)
    if not values:
        return None

    projection = statistics.mean(values)
    volatility = statistics.pstdev(values) if len(values) > 1 else max(abs(projection) * 0.18, 1)
    volatility = max(volatility, 0.25)
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

    team = player.get("Team") or request.team
    validation = []
    if request.team and team and request.team.lower() not in str(team).lower() and str(team).lower() not in request.team.lower():
        validation.append(f"Team mismatch: SportsDataIO lists {normalize_name(player)} on {team}.")

    injury = injury_note(sport, player_id)
    if injury:
        validation.append(f"Injury/status note: {injury}.")

    return {
        "sport": sport,
        "subject": normalize_name(player),
        "team": team,
        "market": request.market.strip(),
        "line": request.line,
        "odds": request.odds,
        "projection": round(statistics.mean(simulated), 2),
        "hit_rate": round(hr, 3),
        "implied_probability": round(implied, 3),
        "edge": round(edge, 3),
        "confidence": round(confidence, 3),
        "recommendation": recommendation,
        "source": "sportsdataio-stats",
        "feed": feed_path,
        "best_lines": relevant_best_lines(sport, request),
        "sample_size": len(values),
        "validation": validation,
        "explanation": (
            f"{normalize_name(player)} {request.market} uses SportsDataIO player data "
            f"({len(values)} stat sample{'s' if len(values) != 1 else ''}) and compares simulated hit rate "
            f"to implied odds probability."
        ),
    }


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
    if sport == "NHL":
        if "shots" in key:
            return 3.2, 1.2
        if "points" in key:
            return 0.85, 0.45
        if "assists" in key:
            return 0.55, 0.35
        if "goals" in key and "against" not in key:
            return 0.36, 0.25
        if "saves" in key:
            return 28, 6
        if "blocked" in key:
            return 1.7, 0.8
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
    stats_prediction = stats_based_prediction(request)
    if stats_prediction:
        stats_prediction["validation"] = [
            *stats_prediction.get("validation", []),
            *context_warnings(request.sport, request.player or request.team or ""),
        ]
        enrich_prediction_result(stats_prediction)
        record_prediction(request, stats_prediction)
        return stats_prediction

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

    result = {
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
        "source": "manual-model",
        "best_lines": relevant_best_lines(sport, request),
        "sample_size": 0,
        "validation": [
            "No player-specific SportsDataIO stat feed was available for this prediction."
        ] if sportsdata_key() else [
            "Live provider not connected. Using manual mode."
        ] + context_warnings(sport, subject),
        "explanation": (
            f"{subject} {market} is projected around {round(statistics.mean(simulated), 2)} against a "
            f"{request.line} line. The model compares simulated hit rate to implied odds probability."
        ),
    }
    enrich_prediction_result(result)
    record_prediction(request, result)
    return result


def record_prediction(request: PredictionRequest, result: dict[str, Any]) -> None:
    prediction_id = f"p{int(time.time() * 1000)}{len(PREDICTION_LOG) % 1000}"
    row = {
        "id": prediction_id,
        "timestamp": int(time.time()),
        "sport": request.sport.upper(),
        "subject": request.player or request.team or result.get("subject"),
        "market": request.market,
        "line": request.line,
        "odds": request.odds,
        "projection": result.get("projection"),
        "recommendation": result.get("recommendation"),
        "confidence": result.get("confidence"),
        "edge": result.get("edge"),
        "risk": result.get("risk"),
        "source": result.get("source"),
        "outcome": "pending",
        "data": result,
    }
    PREDICTION_LOG.append(row)
    del PREDICTION_LOG[:-250]
    if DB_READY:
        db_execute(
            """INSERT INTO predictions
            (id, user_id, timestamp, sport, subject, market, line, odds, projection, recommendation,
             confidence, edge, risk_json, source, outcome, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prediction_id,
                None,
                row["timestamp"],
                row["sport"],
                row["subject"],
                row["market"],
                row["line"],
                row["odds"],
                row["projection"],
                row["recommendation"],
                row["confidence"],
                row["edge"],
                json.dumps(row.get("risk") or {}),
                row["source"],
                row["outcome"],
                json.dumps(result),
            ),
        )


def stored_predictions(limit: int = 250) -> list[dict[str, Any]]:
    if not DB_READY:
        return PREDICTION_LOG[-limit:]
    rows = db_fetchall("SELECT * FROM predictions ORDER BY timestamp DESC LIMIT ?", (limit,))
    output = []
    for row in rows:
        item = {
            "id": row.get("id"),
            "timestamp": row.get("timestamp"),
            "sport": row.get("sport"),
            "subject": row.get("subject"),
            "market": row.get("market"),
            "line": row.get("line"),
            "odds": row.get("odds"),
            "projection": row.get("projection"),
            "recommendation": row.get("recommendation"),
            "confidence": row.get("confidence"),
            "edge": row.get("edge"),
            "risk": json_load(row.get("risk_json"), {}),
            "source": row.get("source"),
            "outcome": row.get("outcome"),
            "closing_line": row.get("closing_line"),
            "closing_odds": row.get("closing_odds"),
            "clv": row.get("clv"),
        }
        output.append(item)
    return list(reversed(output))


def analytics_summary() -> dict[str, Any]:
    rows = stored_predictions()
    by_source: dict[str, int] = {}
    by_sport: dict[str, int] = {}
    by_recommendation: dict[str, int] = {}
    by_confidence: dict[str, int] = {"70%+": 0, "60-69%": 0, "under 60%": 0}
    settled = [row for row in rows if row.get("outcome") in {"win", "loss", "push"}]
    wins = sum(1 for row in settled if row.get("outcome") == "win")
    losses = sum(1 for row in settled if row.get("outcome") == "loss")
    pushes = sum(1 for row in settled if row.get("outcome") == "push")
    clv_rows = [row for row in rows if row.get("clv") is not None]
    avg_clv = statistics.mean([float(row.get("clv") or 0) for row in clv_rows]) if clv_rows else 0
    for row in rows:
        by_source[row.get("source") or "unknown"] = by_source.get(row.get("source") or "unknown", 0) + 1
        by_sport[row.get("sport") or "unknown"] = by_sport.get(row.get("sport") or "unknown", 0) + 1
        by_recommendation[row.get("recommendation") or "unknown"] = by_recommendation.get(row.get("recommendation") or "unknown", 0) + 1
        confidence = row.get("confidence") or 0
        if confidence >= 0.70:
            by_confidence["70%+"] += 1
        elif confidence >= 0.60:
            by_confidence["60-69%"] += 1
        else:
            by_confidence["under 60%"] += 1

    return {
        "total_predictions": len(rows),
        "settled_predictions": len(settled),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate": round(wins / max(1, wins + losses), 3),
        "clv_tracked": len(clv_rows),
        "average_clv": round(avg_clv, 3),
        "by_source": by_source,
        "by_sport": by_sport,
        "by_recommendation": by_recommendation,
        "by_confidence": by_confidence,
        "recent": rows[-25:],
        "note": "Grade recent predictions as win, loss, or push to build model accuracy history.",
    }


def provider_health() -> dict[str, Any]:
    health = {
        "odds_api_connected": bool(odds_api_key()),
        "sportsdata_api_connected": bool(sportsdata_key()),
        "live_events": {},
        "live_odds": {},
        "stats_players": {},
    }
    for sport in SUPPORTED_SPORTS:
        health["live_events"][sport] = bool(fetch_live_events(sport))
        health["live_odds"][sport] = bool(fetch_live_odds(sport))
        players, _ = sportsdata_first(sport, "players")
        health["stats_players"][sport] = isinstance(players, list) and bool(players)
    return health


def infer_sport_from_text(text: str, default: str = "All") -> str:
    lowered = text.lower()
    for sport in SUPPORTED_SPORTS:
        if sport.lower() in lowered:
            return sport
    if default != "All":
        return default.upper()
    if any(word in lowered for word in ["points", "rebounds", "assists", "threes"]):
        return "NBA"
    if any(word in lowered for word in ["shots on goal", "puck", "saves", "goals against", "hockey"]):
        return "NHL"
    if any(word in lowered for word in ["passing", "rushing", "receiving", "touchdown"]):
        return "NFL"
    if any(word in lowered for word in ["hits", "bases", "home run", "strikeouts"]):
        return "MLB"
    if any(word in lowered for word in ["takedown", "fight", "significant strikes"]):
        return "MMA"
    return "NBA"


def infer_market_from_text(text: str, sport: str) -> str:
    lowered = text.lower()
    for market in MARKET_CATALOG.get(sport, []):
        if market.lower() in lowered:
            return market
    aliases = {
        "pts": "Points",
        "boards": "Rebounds",
        "dimes": "Assists",
        "pra": "Points+Rebounds+Assists",
        "3s": "Threes",
        "passing": "Passing Yards",
        "rushing": "Rushing Yards",
        "receiving": "Receiving Yards",
        "bases": "Total Bases",
        "ks": "Pitcher Strikeouts",
        "strikeouts": "Pitcher Strikeouts" if sport == "MLB" else "Significant Strikes",
    }
    for key, market in aliases.items():
        if key in lowered:
            return market
    return MARKET_CATALOG.get(sport, ["Points"])[0]


def extract_line_from_text(text: str, default: float = 0) -> float:
    import re
    matches = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    return float(matches[-1]) if matches else default


def extract_name_from_text(text: str, sport: str, market: str) -> str:
    lowered = text.lower()
    for token in [sport.lower(), market.lower(), "over", "under", "last season", "tonight", "today", "vs", "against"]:
        lowered = lowered.replace(token, " ")
    words = [word.strip(" ?.,!") for word in lowered.split() if word.strip(" ?.,!")]
    if not words:
        return ""
    return " ".join(word.capitalize() for word in words[:3])


def answer_stats_question(request: AskRequest) -> dict[str, Any]:
    question = request.question.strip()
    sport = infer_sport_from_text(question, request.sport)
    market = infer_market_from_text(question, sport)
    line = extract_line_from_text(question, 0)
    name = extract_name_from_text(question, sport, market)

    player = find_sportsdata_player(sport, name) if name and sport in SPORTSDATA_LEAGUES else None
    if player:
        player_name = normalize_name(player)
        values, feed = fetch_recent_player_values(sport, sportsdata_player_id(player), market)
        context = fetch_sports_context(sport, player_name)
        if values:
            average = statistics.mean(values)
            answer = f"{player_name} is averaging {round(average, 2)} {market} across {len(values)} available stat sample{'s' if len(values) != 1 else ''}."
            if line:
                hit = sum(1 for value in values if value > line)
                answer += f" He cleared {line} in {hit}/{len(values)} samples."
            return {
                "question": question,
                "answer": answer,
                "sport": sport,
                "subject": player_name,
                "market": market,
                "source": "sportsdataio-stats",
                "feed": feed,
                "samples": values,
                "context": {
                    "injuries": context["injuries"][:3],
                    "news": context["news"][:3],
                },
            }

    prediction = predict_market(PredictionRequest(
        sport=sport,
        player=name,
        market=market,
        line=line or market_scale(sport, market)[0],
        odds=-110,
    ))
    return {
        "question": question,
        "answer": (
            f"I could not verify a player-specific stat feed for '{name}'. "
            f"The fallback model projects {prediction['subject']} around {prediction['projection']} {market}."
        ),
        "sport": sport,
        "subject": prediction["subject"],
        "market": market,
        "source": prediction.get("source"),
        "prediction": prediction,
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
    return live_nba


def fetch_props() -> dict[str, dict[str, Any]]:
    # Production live pages must not invent player props. Manual simulator
    # entries still work, and live props should come through sportsbook routes.
    return {}


def odds_api_key() -> str | None:
    return os.getenv("ODDS_API_KEY") or os.getenv("THE_ODDS_API_KEY")


def fetch_live_events(sport: str) -> list[dict[str, Any]]:
    key = odds_api_key()
    sport_key = SPORT_KEYS.get(sport.upper())
    if not key or not sport_key:
        return []

    cache_key = f"events:{sport.upper()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events"
    try:
        response = requests.get(url, params={"apiKey": key}, timeout=8)
        response.raise_for_status()
        return cache_set(cache_key, response.json())
    except Exception:
        return []


def normalize_event_card(event: dict[str, Any], sport: str) -> dict[str, Any]:
    home = event.get("home_team") or ""
    away = event.get("away_team") or ""
    profile = find_environment_profile(sport.upper(), home)
    return {
        "event_id": event.get("id"),
        "sport": sport.upper(),
        "home_team": home,
        "away_team": away,
        "matchup": f"{away} at {home}".strip(),
        "commence_time": event.get("commence_time"),
        "venue": profile.get("venue") or "venue pending",
        "surface": profile.get("surface") or "unknown",
        "roof": profile.get("roof") or "unknown",
        "weather_risk": profile.get("weather") or "unknown",
    }


def event_cards(sport: str = "All", limit: int = 12) -> list[dict[str, Any]]:
    sports = SUPPORTED_SPORTS if sport == "All" else [sport.upper()]
    cards: list[dict[str, Any]] = []
    for item in sports:
        cards.extend(normalize_event_card(event, item) for event in fetch_live_events(item)[:limit])
    return sorted(cards, key=lambda row: row.get("commence_time") or "")[:limit]


def fetch_live_odds(sport: str, markets: str = "h2h,spreads,totals") -> list[dict[str, Any]]:
    key = odds_api_key()
    sport_key = SPORT_KEYS.get(sport.upper())
    if not key or not sport_key:
        return []

    cache_key = f"odds:{sport.upper()}:{markets}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": key,
        "regions": "us",
        "markets": markets,
        "oddsFormat": "american",
    }
    try:
        response = requests.get(url, params=params, timeout=8)
        response.raise_for_status()
        return cache_set(cache_key, response.json())
    except Exception:
        return []


def market_for_best_lines(market: str) -> str:
    lowered = market.lower()
    if "spread" in lowered or "run line" in lowered:
        return "spreads"
    if "total" in lowered or "points" in lowered or "runs" in lowered:
        return "totals"
    if "moneyline" in lowered or "winner" in lowered:
        return "h2h"
    return "h2h,spreads,totals"


def price_is_better(candidate: int | float | None, current: int | float | None) -> bool:
    if candidate is None:
        return False
    if current is None:
        return True
    return candidate > current


def line_is_better(market_key: str, outcome_name: str, candidate: Any, current: Any) -> bool:
    if candidate is None:
        return False
    if current is None:
        return True
    try:
        candidate_float = float(candidate)
        current_float = float(current)
    except (TypeError, ValueError):
        return False
    if market_key == "totals" and outcome_name.lower() == "over":
        return candidate_float < current_float
    return candidate_float > current_float


def extract_best_lines(events: list[dict[str, Any]], wanted_market: str = "") -> list[dict[str, Any]]:
    wanted = market_for_best_lines(wanted_market)
    allowed = set(wanted.split(","))
    output = []

    for event in events[:25]:
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for book in event.get("bookmakers", []):
            book_name = book.get("title") or book.get("key")
            for market in book.get("markets", []):
                market_key = market.get("key")
                if market_key not in allowed:
                    continue
                for outcome in market.get("outcomes", []):
                    outcome_name = outcome.get("name", "")
                    group_key = (market_key, outcome_name)
                    current = grouped.get(group_key, {
                        "market": market_key,
                        "outcome": outcome_name,
                        "best_price": None,
                        "best_price_book": None,
                        "best_line": None,
                        "best_line_book": None,
                        "books_checked": 0,
                    })
                    price = outcome.get("price")
                    point = outcome.get("point")
                    if price_is_better(price, current["best_price"]):
                        current["best_price"] = price
                        current["best_price_book"] = book_name
                    if line_is_better(market_key, outcome_name, point, current["best_line"]):
                        current["best_line"] = point
                        current["best_line_book"] = book_name
                    current["books_checked"] += 1
                    grouped[group_key] = current

        if grouped:
            sport_from_key = next((key for key, value in SPORT_KEYS.items() if value == event.get("sport_key")), "All")
            event_card = normalize_event_card(event, sport_from_key)
            output.append({
                "event_id": event.get("id"),
                "sport_key": event.get("sport_key"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
                "venue": event_card.get("venue"),
                "surface": event_card.get("surface"),
                "roof": event_card.get("roof"),
                "weather_risk": event_card.get("weather_risk"),
                "best_lines": list(grouped.values()),
            })

    return output


def relevant_best_lines(sport: str, request: PredictionRequest) -> list[dict[str, Any]]:
    events = fetch_live_odds(sport, market_for_best_lines(request.market))
    if not events:
        return []
    subject = " ".join(part for part in [request.team, request.player] if part).lower()
    rows = extract_best_lines(events, request.market)
    if not subject:
        return rows[:3]
    matched = [
        row for row in rows
        if subject in f"{row.get('home_team', '')} {row.get('away_team', '')}".lower()
        or any(piece and piece in f"{row.get('home_team', '')} {row.get('away_team', '')}".lower() for piece in subject.split())
    ]
    return (matched or rows)[:3]


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


def probability_to_american(probability: float) -> int:
    probability = min(0.99, max(0.01, probability))
    if probability >= 0.5:
        return round(-(probability / (1 - probability)) * 100)
    return round(((1 - probability) / probability) * 100)


def no_vig_probability(probability: float, book_hold: float = 0.047) -> float:
    return min(0.99, max(0.01, probability - book_hold / 2))


def power_rating(subject: str, sport: str, team: str | None, market: str) -> dict[str, Any]:
    base = {
        "NBA": 72,
        "NHL": 69,
        "NFL": 74,
        "MLB": 68,
        "MMA": 66,
    }.get(sport, 66)
    subject_lift = stable_noise(subject, sport, team or "", market, spread=18)
    rest_lift = stable_noise("rest", sport, team or subject, spread=6)
    matchup_lift = stable_noise("matchup", sport, subject, market, spread=10)
    rating = round(base + subject_lift + rest_lift + matchup_lift, 1)
    return {
        "rating": rating,
        "base": base,
        "situational": round(rest_lift, 1),
        "matchup": round(matchup_lift, 1),
        "note": "Synthetic power rating from sport baseline, matchup, and situational adjustment.",
    }


def market_intelligence(result: dict[str, Any]) -> dict[str, Any]:
    implied = result.get("implied_probability") or 0
    hit_rate_value = result.get("hit_rate") or 0
    true_probability = no_vig_probability(hit_rate_value)
    fair_odds = probability_to_american(true_probability)
    posted_odds = result.get("odds") or -110
    edge = result.get("edge") or 0
    if edge >= 0.08:
        signal = "Model is above market"
    elif edge <= -0.05:
        signal = "Market is stronger than model"
    else:
        signal = "Close to market"
    return {
        "posted_implied": round(implied, 3),
        "true_probability": round(true_probability, 3),
        "fair_odds": fair_odds,
        "posted_odds": posted_odds,
        "expected_value": round((true_probability * 100) - ((1 - true_probability) * abs(posted_odds) / 100), 3),
        "vig_note": "Fair odds remove an estimated sportsbook hold from the model probability.",
        "sharp_signal": signal,
        "clv_watch": "Track whether this line closes better or worse than the number you entered.",
    }


def pro_model_layers(result: dict[str, Any]) -> dict[str, Any]:
    sport = result.get("sport") or "All"
    market = (result.get("market") or "").lower()
    advanced = {
        "NBA": ["pace", "usage rate", "rotation/minutes", "shot-zone profile", "late injury scratches"],
        "NFL": ["EPA proxy", "success-rate proxy", "game script", "red-zone role", "weather/coaching tendency"],
        "MLB": ["xERA proxy", "wOBA/contact proxy", "pitcher-vs-lineup split", "bullpen fatigue", "park factor"],
        "NHL": ["Corsi proxy", "expected-goals proxy", "goalie confirmation", "back-to-back fatigue", "power-play role"],
        "MMA": ["style matchup", "strike accuracy", "takedown defense", "cardio/round projection", "finish probability"],
    }.get(sport, ["market probability", "recent form", "matchup context"])
    model_stack = [
        "Baseline projection",
        "Recent-form adjustment",
        "Matchup/situational logic",
        "Monte Carlo simulation",
        "Market-implied probability comparison",
    ]
    if result.get("source") == "sportsdataio-stats":
        model_stack.insert(0, "Player stat feed")
    return {
        "data_engine": {
            "odds": "multi-book best-line scan" if odds_api_key() else "odds key missing; using entered line",
            "stats": "player stat feed connected" if sportsdata_key() else "stat key missing; model fallback active",
            "injuries_news": "context wire connected" if sportsdata_key() else "connect SPORTSDATA_API_KEY for verified lineup/news",
            "validation": "provider-first, fallback-labeled",
        },
        "model_stack": model_stack,
        "simulation": {
            "runs": SIM_RUNS,
            "type": "Monte Carlo",
            "outputs": ["hit rate", "projection", "volatility", "alternate line ladder"],
        },
        "edge_system": {
            "ev": result.get("market_intelligence", {}).get("expected_value"),
            "edge": result.get("edge"),
            "confidence": result.get("confidence"),
            "only_plus_ev": (result.get("edge") or 0) > 0,
        },
        "line_movement": {
            "opening_line": None,
            "current_line": result.get("line"),
            "steam_move": "pending split provider",
            "reverse_line_movement": "pending split provider",
            "sharp_public_note": "Connect a splits provider for % bets vs % money.",
        },
        "sport_specific": advanced,
        "prop_engine": {
            "market": market,
            "alt_lines": bool(result.get("alternate_lines")),
            "usage_minutes_role": sport in {"NBA", "NFL", "NHL"},
            "player_specific": result.get("source") == "sportsdataio-stats",
        },
    }


def find_environment_profile(sport: str, team: str | None) -> dict[str, str]:
    sport_profiles = ENVIRONMENT_PROFILES.get(sport, {})
    if not team:
        return sport_profiles.get("default", {"venue": "unknown venue", "surface": "unknown", "roof": "unknown", "weather": "unknown"})
    lowered = team.lower()
    for name, profile in sport_profiles.items():
        if name != "default" and (lowered in name.lower() or name.lower() in lowered):
            return profile
    return sport_profiles.get("default", {"venue": "unknown venue", "surface": "unknown", "roof": "unknown", "weather": "unknown"})


def playing_environment(result: dict[str, Any]) -> dict[str, Any]:
    sport = result.get("sport") or ""
    market = (result.get("market") or "").lower()
    profile = find_environment_profile(sport, result.get("team"))
    weather_risk = profile.get("weather", "unknown")
    notes = []
    if sport == "NFL":
        if profile.get("roof") in {"dome", "retractable", "canopy"}:
            notes.append("Controlled environment favors passing timing, kicking, and totals stability.")
        elif weather_risk == "high":
            notes.append("Outdoor weather can lower passing efficiency, kicking confidence, and explosive-play rate.")
        if profile.get("surface") == "turf":
            notes.append("Turf can slightly help speed-based routes and yards-after-catch props.")
        elif profile.get("surface") == "grass":
            notes.append("Grass can add footing variance, especially in rain/cold games.")
    elif sport == "MLB":
        if profile.get("roof") == "outdoor" and weather_risk in {"medium", "high"}:
            notes.append("Wind and temperature can materially change carry, totals, and home-run probability.")
        elif profile.get("roof") in {"dome", "retractable"}:
            notes.append("Roof control reduces weather variance for pitcher and hitter props.")
        if "home run" in market or "bases" in market:
            notes.append("Park, weather, and handedness splits matter more for power markets.")
    elif sport in {"NBA", "NHL", "MMA"}:
        notes.append("Indoor environment keeps weather impact low; travel, rest, altitude, and pace matter more.")
    return {
        "venue": profile.get("venue"),
        "surface": profile.get("surface"),
        "roof": profile.get("roof"),
        "weather_risk": weather_risk,
        "notes": notes,
    }


def matchup_intelligence(result: dict[str, Any]) -> dict[str, Any]:
    sport = result.get("sport") or ""
    subject = result.get("subject") or ""
    team = result.get("team") or ""
    market = result.get("market") or ""
    opponent_signal = stable_noise("opponent", sport, subject, team, market, spread=20)
    coaching_signal = stable_noise("coach", sport, team, market, spread=16)
    history_signal = stable_noise("history", sport, subject, team, market, spread=18)
    score = round(50 + opponent_signal + coaching_signal + history_signal)
    if score >= 62:
        lean = "matchup boost"
    elif score <= 42:
        lean = "matchup drag"
    else:
        lean = "neutral matchup"
    return {
        "score": max(1, min(99, score)),
        "lean": lean,
        "history_note": "Player/team history vs opponent is modeled now and can be upgraded with game-log feeds.",
        "coaching_note": "Coaching tendency estimates role, pace, pass/run mix, bullpen usage, or rotation style.",
        "opponent_note": "Opponent weakness signal looks for market-specific vulnerability.",
    }


def risk_tier(confidence: float, edge: float) -> dict[str, Any]:
    if confidence >= 0.68 and edge >= 0.08:
        return {"tier": "Strong edge", "units": 1.0, "label": "1 unit max"}
    if confidence >= 0.60 and edge >= 0.04:
        return {"tier": "Playable", "units": 0.5, "label": "0.5 unit max"}
    if confidence >= 0.54 and edge >= 0:
        return {"tier": "Lean", "units": 0.25, "label": "0.25 unit max"}
    if edge < -0.04:
        return {"tier": "Avoid", "units": 0, "label": "No play"}
    return {"tier": "Watch", "units": 0, "label": "Wait for a better line"}


def model_factors(result: dict[str, Any]) -> list[dict[str, Any]]:
    projection = result.get("projection") or 0
    line = result.get("line") or 0
    edge = result.get("edge") or 0
    hit_rate_value = result.get("hit_rate") or 0
    implied = result.get("implied_probability") or 0
    return [
        {
            "name": "Projection gap",
            "value": round(projection - line, 2),
            "note": f"Projected {projection} vs line {line}",
        },
        {
            "name": "Hit rate gap",
            "value": round(hit_rate_value - implied, 3),
            "note": f"Model hit {round(hit_rate_value * 100)}% vs implied {round(implied * 100)}%",
        },
        {
            "name": "Market edge",
            "value": round(edge, 3),
            "note": "Positive is better for overs or selected side.",
        },
    ]


def alternate_lines(result: dict[str, Any]) -> list[dict[str, Any]]:
    sport = result.get("sport") or ""
    market = result.get("market") or ""
    line = float(result.get("line") or 0)
    projection = float(result.get("projection") or line)
    _, volatility = market_scale(sport, market)
    step = 0.5
    if line >= 100:
        step = 10
    elif line >= 20:
        step = 2.5
    elif "saves" in market.lower():
        step = 2.5
    candidates = [line - (2 * step), line - step, line, line + step, line + (2 * step)]
    rows = []
    for alt_line in candidates:
        if alt_line <= 0:
            continue
        z = (projection - alt_line) / max(volatility, 0.1)
        probability = max(0.03, min(0.97, 0.5 + z * 0.18))
        edge = probability - odds_to_prob(int(result.get("odds") or -110))
        rows.append({
            "line": round(alt_line, 2),
            "hit_rate": round(probability, 3),
            "fair_odds": probability_to_american(no_vig_probability(probability)),
            "edge": round(edge, 3),
            "risk": risk_tier(probability, edge),
        })
    return rows


def enrich_prediction_result(result: dict[str, Any]) -> dict[str, Any]:
    result["risk"] = risk_tier(result.get("confidence") or 0, result.get("edge") or 0)
    result["factors"] = model_factors(result)
    result["power_rating"] = power_rating(
        result.get("subject") or "",
        result.get("sport") or "",
        result.get("team"),
        result.get("market") or "",
    )
    result["market_intelligence"] = market_intelligence(result)
    result["environment"] = playing_environment(result)
    result["matchup_intelligence"] = matchup_intelligence(result)
    result["alternate_lines"] = alternate_lines(result)
    result["pro_layers"] = pro_model_layers(result)
    return result


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


def live_market_rankings(sport: str) -> list[dict[str, Any]]:
    events = fetch_live_odds(sport, "h2h,spreads,totals")
    rows = []
    for event in extract_best_lines(events):
        matchup = f"{event.get('away_team')} at {event.get('home_team')}"
        for line in event.get("best_lines", []):
            price = line.get("best_price")
            point = line.get("best_line")
            # This is a line-shopping score, not a pick quality score.
            price_score = (int(price) + 200) / 4 if isinstance(price, int) else 50
            book_depth = min(line.get("books_checked", 0), 12) * 2
            confidence = max(45, min(86, round(price_score + book_depth)))
            rows.append({
                "name": line.get("outcome") or matchup,
                "team": event.get("home_team"),
                "opponent": event.get("away_team"),
                "sport": sport,
                "market": line.get("market"),
                "line": point,
                "odds": price,
                "confidence": confidence,
                "source": "live-best-line",
                "book": line.get("best_price_book") or line.get("best_line_book"),
                "matchup": matchup,
                "commence_time": event.get("commence_time"),
                "venue": event.get("venue"),
                "surface": event.get("surface"),
                "roof": event.get("roof"),
            })
    return rows


def ranking_rows(sport: str = "All", team: str = "All") -> dict[str, Any]:
    sports = SUPPORTED_SPORTS if sport == "All" else [sport.upper()]
    live_rows = []
    for item in sports:
        live_rows.extend(live_market_rankings(item))

    if live_rows:
        rows = live_rows
        source = "live-best-lines"
    else:
        rows = []
        source = "live-provider-unavailable"

    if sport != "All":
        rows = [row for row in rows if row.get("sport") == sport.upper()]
    if team != "All":
        lowered = team.lower()
        rows = [
            row for row in rows
            if lowered in " ".join(str(row.get(key, "")) for key in ["name", "team", "opponent", "matchup"]).lower()
        ]

    rows = sorted(rows, key=lambda row: row.get("confidence", 0), reverse=True)[:50]
    return {
        "source": source,
        "providers": {
            "odds_api_connected": bool(odds_api_key()),
            "sportsdata_api_connected": bool(sportsdata_key()),
        },
        "rankings": rows,
    }


def live_insight_rows(sport: str = "All", query: str = "") -> dict[str, Any]:
    sports = SUPPORTED_SPORTS if sport == "All" else [sport.upper()]
    rows = []

    for item in sports:
        for event in extract_best_lines(fetch_live_odds(item, "h2h,spreads,totals"))[:8]:
            matchup = f"{event.get('away_team')} at {event.get('home_team')}"
            best = sorted(event.get("best_lines", []), key=lambda line: line.get("books_checked", 0), reverse=True)[:3]
            for line in best:
                rows.append({
                    "type": "Market",
                    "sport": item,
                    "title": f"Best {line.get('market')} price: {line.get('outcome')}",
                    "body": f"{matchup}. Best price {line.get('best_price')} at {line.get('best_price_book')}; best line {line.get('best_line')} at {line.get('best_line_book')}.",
                    "player": line.get("outcome") or matchup,
                    "score": min(95, 65 + int(line.get("books_checked", 0) * 2)),
                    "source": "live-best-lines",
                })

        context = fetch_sports_context(item, query)
        for injury in context["injuries"][:8]:
            rows.append({
                "type": "Injury",
                "sport": item,
                "title": f"{injury.get('player') or 'Player'} status watch",
                "body": " / ".join(str(part) for part in [injury.get("team"), injury.get("status"), injury.get("body_part"), injury.get("updated")] if part),
                "player": injury.get("player"),
                "score": 82,
                "source": "sportsdataio-injury-wire",
            })
        for news_item in context["news"][:8]:
            rows.append({
                "type": "News",
                "sport": item,
                "title": news_item.get("title") or "News update",
                "body": news_item.get("summary") or "",
                "player": news_item.get("player") or news_item.get("team"),
                "score": 74,
                "source": news_item.get("source") or "sportsdataio-news",
            })

    if query:
        lowered = query.lower()
        rows = [
            row for row in rows
            if lowered in " ".join(str(row.get(key, "")) for key in ["title", "body", "player", "sport", "type"]).lower()
        ]

    return {
        "source": "live-context" if rows else "live-provider-unavailable",
        "providers": {
            "odds_api_connected": bool(odds_api_key()),
            "sportsdata_api_connected": bool(sportsdata_key()),
        },
        "message": "Live provider not connected. Using manual mode." if not rows else "Live insight feed loaded.",
        "insights": sorted(rows, key=lambda row: row.get("score", 0), reverse=True)[:60],
    }


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
    live_sports = []
    for sport in SUPPORTED_SPORTS:
      if fetch_live_odds(sport):
          live_sports.append(sport)

    mode = "live odds + stats engine" if live_sports and sportsdata_key() else (
        "live odds engine" if live_sports else "manual mode"
    )

    return {
        "mode": mode,
        "message": "Live provider not connected. Using manual mode." if not live_sports else "Live odds feed loaded.",
        "providers": {
            "odds_api_connected": bool(odds_api_key()),
            "sportsdata_api_connected": bool(sportsdata_key()),
            "live_odds_sports": live_sports,
        },
        "top_bets": sharp[:10],
        "all_bets": ranked,
        "parlay": build_parlay(sharp),
        "insights": insights(players),
        "first_shot": first_action(players, history),
        "events": event_cards("All", 10),
        "updated_at": int(time.time()),
    }


def loop() -> None:
    global LATEST
    while True:
        LATEST = engine_tick()
        time.sleep(POLL_INTERVAL)


def refresh_daily_feeds() -> dict[str, Any]:
    refreshed = []
    for sport in SUPPORTED_SPORTS:
        fetch_live_events(sport)
        fetch_live_odds(sport)
        if sport in SPORTSDATA_LEAGUES:
            sportsdata_first(sport, "players")
            sportsdata_first(sport, "teams")
            sportsdata_first(sport, "injuries")
            sportsdata_first(sport, "news")
        refreshed.append(sport)
    LAST_DAILY_REFRESH.update({
        "timestamp": int(time.time()),
        "status": "ok",
        "sports": refreshed,
    })
    return LAST_DAILY_REFRESH


def daily_refresh_loop() -> None:
    while True:
        try:
            refresh_daily_feeds()
        except Exception as exc:
            LAST_DAILY_REFRESH.update({
                "timestamp": int(time.time()),
                "status": f"error: {exc}",
                "sports": [],
            })
        time.sleep(DAILY_REFRESH_INTERVAL)


@app.on_event("startup")
def startup() -> None:
    init_db()
    LATEST.update(engine_tick())
    threading.Thread(target=loop, daemon=True).start()
    threading.Thread(target=daily_refresh_loop, daemon=True).start()


@app.get("/api")
def api() -> dict[str, Any]:
    return LATEST


@app.get("/api/catalog")
def catalog() -> dict[str, Any]:
    return {
        "teams": TEAM_CATALOG,
        "markets": MARKET_CATALOG,
        "players": [],
        "providers": {
            "odds_api_connected": bool(odds_api_key()),
            "sportsdata_api_connected": bool(sportsdata_key()),
            "odds_api_env_vars": ["ODDS_API_KEY", "THE_ODDS_API_KEY"],
            "sportsdata_api_env_vars": ["SPORTSDATA_API_KEY", "SPORTS_DATA_API_KEY"],
            "news_context_endpoints": ["/api/news/{sport}", "/api/context/{sport}"],
            "best_line_endpoint": "/api/best-lines/{sport}",
        },
    }


@app.get("/api/live-board")
def live_board(sport: str = "All", team: str = "All") -> dict[str, Any]:
    rankings_data = ranking_rows(sport, team)
    insights_data = live_insight_rows(sport, "")
    snapshot = LATEST if LATEST.get("all_bets") else engine_tick()
    return {
        "sport": sport,
        "team": team,
        "rankings": rankings_data.get("rankings", []),
        "insights": insights_data.get("insights", []),
        "engine": snapshot,
        "providers": {
            **rankings_data.get("providers", {}),
            "weather_api_connected": bool(weather_api_key()),
            "database_ready": DB_READY,
        },
        "source": rankings_data.get("source"),
        "updated_at": int(time.time()),
    }


@app.get("/api/players/{sport}")
def players_search(sport: str, q: str = "") -> dict[str, Any]:
    sport = sport.upper()
    players, path = sportsdata_first(sport, "players")
    if not isinstance(players, list):
        return {
            "sport": sport,
            "source": "live-provider-unavailable",
            "message": "Live provider not connected. Using manual mode.",
            "players": [],
        }

    lowered = q.lower().strip()
    matched = []
    for player in players:
        name = normalize_name(player)
        if not lowered or lowered in name.lower():
            matched.append({
                "id": sportsdata_player_id(player),
                "name": name,
                "team": player.get("Team"),
                "position": player.get("Position"),
                "status": player.get("Status") or player.get("InjuryStatus"),
            })
        if len(matched) >= 25:
            break

    return {
        "sport": sport,
        "source": "sportsdataio",
        "feed": path,
        "players": matched,
    }


@app.get("/api/events/{sport}")
def events(sport: str) -> dict[str, Any]:
    live_events = fetch_live_events(sport)
    return {
        "sport": sport.upper(),
        "source": "the-odds-api" if live_events else "catalog-fallback",
        "events": [normalize_event_card(event, sport) for event in live_events],
        "teams": TEAM_CATALOG.get(sport.upper(), []),
    }


@app.get("/api/odds/{sport}")
def odds(sport: str) -> dict[str, Any]:
    live_odds = fetch_live_odds(sport)
    return {
        "sport": sport.upper(),
        "source": "the-odds-api" if live_odds else "live-provider-unavailable",
        "odds": live_odds,
    }


@app.get("/api/rankings")
def rankings(sport: str = "All", team: str = "All") -> dict[str, Any]:
    return ranking_rows(sport, team)


@app.get("/api/insights")
def insights_api(sport: str = "All", q: str = "") -> dict[str, Any]:
    return live_insight_rows(sport, q)


@app.get("/api/best-lines/{sport}")
def best_lines(sport: str, market: str = "") -> dict[str, Any]:
    live_odds = fetch_live_odds(sport, market_for_best_lines(market))
    return {
        "sport": sport.upper(),
        "market": market,
        "source": "the-odds-api" if live_odds else "odds-fallback",
        "best_lines": extract_best_lines(live_odds, market),
    }


@app.get("/api/market-sources")
def market_sources() -> dict[str, Any]:
    return {
        "sources": MARKET_SOURCE_STACK,
        "framework": [
            "Project true probability.",
            "Remove vig from posted odds.",
            "Compare fair odds to the available book price.",
            "Check best line across books.",
            "Flag sharp/public movement when split data is connected.",
            "Add injury, weather, rest, travel, and matchup context.",
            "Track closing line value and settled accuracy.",
        ],
        "connected": {
            "best_lines": bool(odds_api_key()),
            "player_stats": bool(sportsdata_key()),
            "sharp_splits": False,
            "crowd_probability": False,
        },
    }


@app.get("/api/news/{sport}")
def news(sport: str, q: str = "") -> dict[str, Any]:
    return fetch_sports_context(sport, q)


@app.get("/api/context/{sport}")
def context(sport: str, q: str = "") -> dict[str, Any]:
    return fetch_sports_context(sport, q)


@app.get("/api/analytics")
def analytics() -> dict[str, Any]:
    return analytics_summary()


@app.post("/api/auth/register")
def register_user(request: UserAuthRequest) -> dict[str, Any]:
    if not DB_READY:
        return {"ok": False, "error": "Database is not ready."}
    username = request.username.strip().lower()
    if len(username) < 3 or len(request.password) < 6:
        return {"ok": False, "error": "Use a username with 3+ characters and password with 6+ characters."}
    user_id = secrets.token_urlsafe(10)
    salt = secrets.token_hex(12)
    try:
        db_execute(
            "INSERT INTO users (id, username, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, hash_password(request.password, salt), salt, int(time.time())),
        )
    except Exception:
        return {"ok": False, "error": "That username is already taken."}
    token = secrets.token_urlsafe(32)
    db_execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, user_id, int(time.time())))
    return {"ok": True, "token": token, "user": {"id": user_id, "username": username}}


@app.post("/api/auth/login")
def login_user(request: UserAuthRequest) -> dict[str, Any]:
    if not DB_READY:
        return {"ok": False, "error": "Database is not ready."}
    username = request.username.strip().lower()
    user = db_fetchone("SELECT * FROM users WHERE username = ?", (username,))
    if not user or user.get("password_hash") != hash_password(request.password, user.get("salt") or ""):
        return {"ok": False, "error": "Invalid username or password."}
    token = secrets.token_urlsafe(32)
    db_execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, user["id"], int(time.time())))
    return {"ok": True, "token": token, "user": {"id": user["id"], "username": username}}


@app.get("/api/me")
def me(token: str = "") -> dict[str, Any]:
    user = user_from_token(token)
    return {"ok": bool(user), "user": user}


@app.post("/api/watchlist")
def save_watch(request: WatchlistRequest) -> dict[str, Any]:
    user = user_from_token(request.token)
    item_id = secrets.token_urlsafe(12)
    db_execute(
        """INSERT INTO watchlist (id, user_id, subject, sport, market, line, odds, threshold, created_at, last_signal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            item_id,
            user.get("id") if user else None,
            request.subject,
            request.sport.upper(),
            request.market,
            request.line,
            request.odds,
            request.threshold,
            int(time.time()),
            "created",
        ),
    )
    return {"ok": True, "watch": {"id": item_id, **request.dict(exclude={"token"})}}


@app.get("/api/watchlist")
def get_watchlist(token: str = "") -> dict[str, Any]:
    user = user_from_token(token)
    if user:
        rows = db_fetchall("SELECT * FROM watchlist WHERE user_id = ? ORDER BY created_at DESC LIMIT 100", (user["id"],))
    else:
        rows = db_fetchall("SELECT * FROM watchlist WHERE user_id IS NULL ORDER BY created_at DESC LIMIT 50")
    return {"ok": True, "watchlist": rows}


@app.post("/api/cards")
def save_card(request: SavedCardRequest) -> dict[str, Any]:
    user = user_from_token(request.token)
    card_id = secrets.token_urlsafe(12)
    db_execute(
        "INSERT INTO saved_cards (id, user_id, name, legs_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (card_id, user.get("id") if user else None, request.name, json.dumps(request.legs), int(time.time())),
    )
    return {"ok": True, "card": {"id": card_id, "name": request.name, "legs": request.legs}}


@app.get("/api/cards")
def get_cards(token: str = "") -> dict[str, Any]:
    user = user_from_token(token)
    if user:
        rows = db_fetchall("SELECT * FROM saved_cards WHERE user_id = ? ORDER BY created_at DESC LIMIT 100", (user["id"],))
    else:
        rows = db_fetchall("SELECT * FROM saved_cards WHERE user_id IS NULL ORDER BY created_at DESC LIMIT 50")
    for row in rows:
        row["legs"] = json_load(row.pop("legs_json", None), [])
    return {"ok": True, "cards": rows}


@app.post("/api/alerts")
def create_alert(request: AlertRequest) -> dict[str, Any]:
    user = user_from_token(request.token)
    alert_id = secrets.token_urlsafe(12)
    db_execute(
        """INSERT INTO alerts (id, user_id, subject, sport, market, threshold, status, created_at, last_checked, last_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (alert_id, user.get("id") if user else None, request.subject, request.sport.upper(), request.market, request.threshold, "active", int(time.time()), None, None),
    )
    return {"ok": True, "alert": {"id": alert_id, **request.dict(exclude={"token"})}}


@app.get("/api/alerts")
def get_alerts(token: str = "") -> dict[str, Any]:
    user = user_from_token(token)
    if user:
        rows = db_fetchall("SELECT * FROM alerts WHERE user_id = ? ORDER BY created_at DESC LIMIT 100", (user["id"],))
    else:
        rows = db_fetchall("SELECT * FROM alerts WHERE user_id IS NULL ORDER BY created_at DESC LIMIT 50")
    return {"ok": True, "alerts": rows}


@app.post("/api/alerts/check")
def check_alerts() -> dict[str, Any]:
    rows = db_fetchall("SELECT * FROM alerts WHERE status = 'active' LIMIT 100")
    triggered = []
    for row in rows:
        prediction = predict_market(PredictionRequest(
            sport=row.get("sport") or "NFL",
            player=row.get("subject"),
            market=row.get("market") or "Moneyline",
            line=0.5,
            odds=-110,
        ))
        confidence = prediction.get("confidence") or 0
        message = "watching"
        if confidence >= float(row.get("threshold") or 0.6):
            message = f"{row.get('subject')} crossed {round(confidence * 100)}% confidence for {row.get('market')}."
            triggered.append({"alert": row, "prediction": prediction, "message": message})
        db_execute(
            "UPDATE alerts SET last_checked = ?, last_message = ? WHERE id = ?",
            (int(time.time()), message, row["id"]),
        )
    return {"ok": True, "checked": len(rows), "triggered": triggered}


@app.post("/api/predictions/{prediction_id}/grade")
def grade_prediction(prediction_id: str, request: OutcomeRequest) -> dict[str, Any]:
    outcome = request.outcome.lower().strip()
    if outcome not in {"win", "loss", "push", "pending"}:
        return {"ok": False, "error": "Outcome must be win, loss, push, or pending."}
    for row in PREDICTION_LOG:
        if row.get("id") == prediction_id:
            row["outcome"] = outcome
            row["graded_at"] = int(time.time())
    if DB_READY:
        db_execute(
            "UPDATE predictions SET outcome = ? WHERE id = ?",
            (outcome, prediction_id),
        )
        stored = db_fetchone("SELECT * FROM predictions WHERE id = ?", (prediction_id,))
        if stored:
            return {"ok": True, "prediction": stored, "analytics": analytics_summary()}
    for row in PREDICTION_LOG:
        if row.get("id") == prediction_id:
            return {"ok": True, "prediction": row, "analytics": analytics_summary()}
    return {"ok": False, "error": "Prediction was not found."}


@app.post("/api/predictions/{prediction_id}/closing-line")
def update_closing_line(prediction_id: str, closing_line: float, closing_odds: int = -110) -> dict[str, Any]:
    row = db_fetchone("SELECT * FROM predictions WHERE id = ?", (prediction_id,)) if DB_READY else None
    if not row:
        row = next((item for item in PREDICTION_LOG if item.get("id") == prediction_id), None)
    if not row:
        return {"ok": False, "error": "Prediction was not found."}
    entry_line = float(row.get("line") or 0)
    entry_odds = int(row.get("odds") or -110)
    # Positive CLV means your entry number was better than the later closing number.
    line_clv = entry_line - closing_line
    odds_clv = odds_to_prob(closing_odds) - odds_to_prob(entry_odds)
    clv = round(line_clv + odds_clv, 3)
    if DB_READY:
        db_execute(
            "UPDATE predictions SET closing_line = ?, closing_odds = ?, clv = ? WHERE id = ?",
            (closing_line, closing_odds, clv, prediction_id),
        )
    return {"ok": True, "id": prediction_id, "entry_line": entry_line, "closing_line": closing_line, "clv": clv}


@app.get("/api/admin/status")
def admin_status() -> dict[str, Any]:
    return {
        "providers": provider_health(),
        "cache_entries": len(CACHE),
        "prediction_log_size": len(PREDICTION_LOG),
        "engine_mode": LATEST.get("mode"),
        "database": {
            "ready": DB_READY,
            "type": "postgres" if postgres_enabled() else "sqlite",
            "persistent_on_render": postgres_enabled(),
        },
        "weather_api_connected": bool(weather_api_key()),
        "daily_refresh": LAST_DAILY_REFRESH,
        "refresh_policy": DATA_REFRESH_POLICY,
        "updated_at": int(time.time()),
    }


@app.get("/api/data-freshness")
def data_freshness() -> dict[str, Any]:
    now = int(time.time())
    return {
        "now": now,
        "daily_refresh": LAST_DAILY_REFRESH,
        "refresh_policy": DATA_REFRESH_POLICY,
        "cache_entries": len(CACHE),
        "cache_keys": sorted(CACHE.keys())[:80],
    }


@app.get("/api/weather-context/{sport}")
def weather_context_api(sport: str, team: str = "") -> dict[str, Any]:
    return weather_context(sport, team)


@app.get("/api/responsible-use")
def responsible_use() -> dict[str, Any]:
    return {
        "title": "Research only",
        "helpline": {
            "call": "1-800-MY-RESET",
            "text": "800GAM",
            "chat": "https://www.ncpgambling.org/chat/",
            "source": "National Council on Problem Gambling",
        },
        "rules": [
            "Predictions are not guarantees.",
            "Use confidence, fair odds, CLV, injury news, and best-line checks together.",
            "Avoid chasing losses and use conservative unit sizing.",
            "Do not use this as financial advice.",
            "If gambling is causing problems for you or someone you know, call 1-800-MY-RESET, text 800GAM, or use the NCPG chat for free confidential help.",
        ],
    }


@app.post("/api/settlement/run")
def settlement_run() -> dict[str, Any]:
    # Full automatic settlement requires final stat feeds for each market.
    pending = [row for row in stored_predictions() if row.get("outcome") == "pending"]
    return {
        "ok": True,
        "checked": len(pending),
        "settled": 0,
        "status": "waiting_for_stat_settlement_provider",
        "note": "Connect a final box-score/stat feed to automatically mark win/loss/push.",
    }


@app.post("/api/admin/refresh")
def admin_refresh() -> dict[str, Any]:
    LATEST.update(engine_tick())
    return {
        "ok": True,
        "engine": LATEST,
        "daily_refresh": refresh_daily_feeds(),
    }


@app.post("/api/predict")
def predict(request: PredictionRequest) -> dict[str, Any]:
    return predict_market(request)


@app.post("/api/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    return answer_stats_question(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    html = (BASE_DIR / "index.html").read_text(encoding="utf-8")
    return html.replace('href="styles.css"', 'href="/static/styles.css"').replace('src="app.js"', 'src="/static/app.js"')
