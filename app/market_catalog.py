from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SUPPORTED_SPORTS = ("NBA", "NFL", "MLB", "NHL", "MMA")
SUPPORTED_SPORTBOOKS = ("DraftKings", "FanDuel")

UNCONNECTED_MESSAGE = "Live sportsbook provider not connected."

MARKET_GROUPS: dict[str, list[str]] = {
    "NBA": [
        "moneyline", "spread", "total", "team total", "1Q moneyline", "1Q spread", "1Q total",
        "1H moneyline", "1H spread", "1H total", "player points", "player rebounds",
        "player assists", "player threes", "player steals", "player blocks", "player turnovers",
        "PRA", "PR", "PA", "RA", "double double", "triple double", "first basket",
        "first team basket", "first three pointer", "alt points", "alt rebounds", "alt assists",
        "alt threes",
    ],
    "NFL": [
        "moneyline", "spread", "total", "team total", "1H spread", "1H total", "passing yards",
        "passing touchdowns", "interceptions", "rushing yards", "rushing attempts", "receiving yards",
        "receptions", "longest reception", "anytime touchdown", "first touchdown", "field goals",
        "sacks", "tackles", "fantasy score", "alt passing yards", "alt rushing yards",
        "alt receiving yards",
    ],
    "MLB": [
        "moneyline", "run line", "total", "team total", "first 5 innings ML",
        "first 5 innings spread", "first 5 innings total", "pitcher strikeouts",
        "pitcher outs recorded", "pitcher earned runs", "hitter hits", "hitter total bases",
        "hitter home runs", "hitter RBIs", "hitter runs", "hitter walks", "stolen bases",
        "first home run", "first RBI", "alt strikeouts", "alt total bases",
    ],
    "NHL": [
        "moneyline", "puck line", "total", "team total", "regulation ML", "1P moneyline",
        "1P spread", "1P total", "player shots on goal", "player points", "player goals",
        "player assists", "goalie saves", "power play point", "anytime goal scorer",
        "first goal scorer", "alt shots", "alt saves",
    ],
    "MMA": [
        "fight winner", "moneyline", "method of victory", "KO/TKO", "submission", "decision",
        "round betting", "fight goes distance", "fight does not go distance", "total rounds over/under",
        "win in round 1", "win in round 2", "win in round 3", "significant strikes",
        "takedowns", "submission attempts",
    ],
}

ODDS_API_MARKET_MAP = {
    "h2h": "moneyline",
    "spreads": "spread",
    "totals": "total",
    "team_totals": "team total",
    "alternate_spreads": "alt spread",
    "alternate_totals": "alt total",
    "player_points": "player points",
    "player_rebounds": "player rebounds",
    "player_assists": "player assists",
    "player_threes": "player threes",
    "player_steals": "player steals",
    "player_blocks": "player blocks",
    "player_turnovers": "player turnovers",
    "player_points_rebounds_assists": "PRA",
    "player_points_rebounds": "PR",
    "player_points_assists": "PA",
    "player_rebounds_assists": "RA",
    "player_pass_yds": "passing yards",
    "player_pass_tds": "passing touchdowns",
    "player_interceptions": "interceptions",
    "player_rush_yds": "rushing yards",
    "player_rush_attempts": "rushing attempts",
    "player_reception_yds": "receiving yards",
    "player_receptions": "receptions",
    "player_anytime_td": "anytime touchdown",
    "player_1st_td": "first touchdown",
    "pitcher_strikeouts": "pitcher strikeouts",
    "pitcher_outs": "pitcher outs recorded",
    "pitcher_earned_runs": "pitcher earned runs",
    "batter_hits": "hitter hits",
    "batter_total_bases": "hitter total bases",
    "batter_home_runs": "hitter home runs",
    "batter_rbis": "hitter RBIs",
    "batter_runs": "hitter runs",
    "batter_walks": "hitter walks",
    "player_shots_on_goal": "player shots on goal",
    "player_goals": "player goals",
    "player_power_play_points": "power play point",
    "player_saves": "goalie saves",
    "player_goal_scorer_anytime": "anytime goal scorer",
    "player_goal_scorer_first": "first goal scorer",
    "fight_winner": "fight winner",
    "method_of_victory": "method of victory",
    "fight_goes_distance": "fight goes distance",
    "fight_does_not_go_distance": "fight does not go distance",
    "total_rounds": "total rounds over/under",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_sport(sport: str | None) -> str:
    value = (sport or "").upper().replace("UFC", "MMA")
    if value not in SUPPORTED_SPORTS:
        raise ValueError("sport must be NBA, NFL, MLB, NHL, or MMA")
    return value


def clean_book(book: str | None) -> str | None:
    if not book:
        return None
    normalized = book.strip().lower().replace(" ", "")
    if normalized in {"draftkings", "dk"}:
        return "DraftKings"
    if normalized in {"fanduel", "fd"}:
        return "FanDuel"
    return book.strip()


def book_matches(bookmaker: dict[str, Any], target: str | None = None) -> bool:
    title = clean_book(str(bookmaker.get("title") or bookmaker.get("sportsbook") or bookmaker.get("key") or ""))
    if title not in SUPPORTED_SPORTBOOKS:
        return False
    return target is None or title == clean_book(target)


def infer_market_group(raw_key: str, outcome: dict[str, Any] | None = None) -> str:
    key = (raw_key or "").strip()
    if key in ODDS_API_MARKET_MAP:
        return ODDS_API_MARKET_MAP[key]
    lowered = key.replace("_", " ").strip()
    if outcome and outcome.get("description") and lowered.startswith("player "):
        return lowered
    return lowered or "unknown"


def infer_market_type(sport: str, group: str) -> str:
    g = group.lower()
    if sport == "MMA" and g not in {"moneyline", "fight winner", "total"}:
        return "fighter_prop"
    if any(token in g for token in ["player", "pitcher", "hitter", "touchdown", "goal scorer", "significant strikes", "takedowns"]):
        return "player_prop"
    if any(token in g for token in ["team total", "first team"]):
        return "team_prop"
    if any(token in g for token in ["1q", "1p", "1h", "first 5", "inning", "period", "quarter"]):
        return "period_prop"
    return "game_market"


def infer_side(outcome: dict[str, Any]) -> str | None:
    name = str(outcome.get("name") or "").strip().lower()
    if name in {"over", "under"}:
        return name
    if name.startswith("over "):
        return "over"
    if name.startswith("under "):
        return "under"
    return None


def build_selection(outcome: dict[str, Any], group: str) -> str:
    description = str(outcome.get("description") or "").strip()
    name = str(outcome.get("name") or "").strip()
    point = outcome.get("point")
    if description and name.lower() in {"over", "under"} and point is not None:
        return f"{description} {name.lower()} {point} {group}"
    if description and point is not None:
        return f"{description} {name} {point} {group}".strip()
    if point is not None and name:
        return f"{name} {point} {group}".strip()
    return name or description or group


def normalize_market(
    *,
    sport: str,
    sportsbook: str,
    event_id: str,
    game: str,
    market_key: str,
    outcome: dict[str, Any],
    start_time: str | None = None,
    last_updated: str | None = None,
    source: str = "provider",
    home_team: str | None = None,
    away_team: str | None = None,
) -> dict[str, Any]:
    sport = clean_sport(sport)
    sportsbook = clean_book(sportsbook) or sportsbook
    group = infer_market_group(market_key, outcome)
    player_name = str(outcome.get("description") or "").strip() or None
    team = str(outcome.get("name") or "").strip() or None
    side = infer_side(outcome)
    if side and player_name:
        team = str(outcome.get("team") or "").strip() or None
    opponent = None
    if team and home_team and away_team:
        if team.lower() in home_team.lower():
            opponent = away_team
        elif team.lower() in away_team.lower():
            opponent = home_team

    price = outcome.get("price", outcome.get("odds"))
    try:
        price = int(price)
    except (TypeError, ValueError):
        price = None
    line = outcome.get("point", outcome.get("line"))
    try:
        line = float(line) if line is not None else None
    except (TypeError, ValueError):
        line = None

    return {
        "sport": sport,
        "sportsbook": sportsbook,
        "event_id": str(event_id),
        "game": game,
        "market_type": infer_market_type(sport, group),
        "market_group": group,
        "selection": build_selection(outcome, group),
        "player_name": player_name,
        "team": team,
        "opponent": opponent,
        "side": side,
        "line": line,
        "odds": price,
        "start_time": start_time,
        "last_updated": last_updated or now_iso(),
        "source": source,
    }


def normalize_odds_api_events(
    events: list[dict[str, Any]],
    sport: str,
    sportsbook: str | None = None,
) -> list[dict[str, Any]]:
    sport = clean_sport(sport)
    target_book = clean_book(sportsbook)
    markets: list[dict[str, Any]] = []
    for event in events or []:
        home = event.get("home_team") or ""
        away = event.get("away_team") or ""
        game = f"{away} vs {home}".strip(" vs")
        for bookmaker in event.get("bookmakers", []):
            if not book_matches(bookmaker, target_book):
                continue
            book_title = clean_book(bookmaker.get("title") or bookmaker.get("key")) or str(bookmaker.get("title") or "")
            book_updated = bookmaker.get("last_update")
            for market in bookmaker.get("markets", []):
                market_updated = market.get("last_update") or book_updated
                for outcome in market.get("outcomes", []):
                    if outcome.get("price") is None:
                        continue
                    markets.append(normalize_market(
                        sport=sport,
                        sportsbook=book_title,
                        event_id=event.get("id") or "",
                        game=game,
                        market_key=market.get("key") or "",
                        outcome=outcome,
                        start_time=event.get("commence_time"),
                        last_updated=market_updated,
                        source="The Odds API",
                        home_team=home,
                        away_team=away,
                    ))
    return markets


def filter_markets(
    markets: list[dict[str, Any]],
    *,
    sport: str | None = None,
    sportsbook: str | None = None,
    event_id: str | None = None,
    market_group: str | None = None,
    player_name: str | None = None,
    team: str | None = None,
) -> list[dict[str, Any]]:
    sport_value = sport.upper().replace("UFC", "MMA") if sport else None
    book_value = clean_book(sportsbook)
    group_value = market_group.lower() if market_group else None
    player_value = player_name.lower() if player_name else None
    team_value = team.lower() if team else None
    output: list[dict[str, Any]] = []
    for market in markets:
        if sport_value and market.get("sport") != sport_value:
            continue
        if book_value and clean_book(market.get("sportsbook")) != book_value:
            continue
        if event_id and market.get("event_id") != event_id:
            continue
        if group_value and group_value not in str(market.get("market_group", "")).lower():
            continue
        if player_value and player_value not in str(market.get("player_name") or market.get("selection") or "").lower():
            continue
        if team_value:
            haystack = " ".join(str(market.get(key) or "") for key in ("team", "opponent", "game", "selection")).lower()
            if team_value not in haystack:
                continue
        output.append(market)
    return output


def search_markets(markets: list[dict[str, Any]], query: str, **filters: Any) -> list[dict[str, Any]]:
    query_value = (query or "").strip().lower()
    filtered = filter_markets(markets, **filters)
    if not query_value:
        return filtered
    keys = ("selection", "player_name", "team", "opponent", "game", "market_group", "market_type", "sport", "sportsbook")
    tokens = [token for token in query_value.split() if token]
    return [
        market for market in filtered
        if all(token in " ".join(str(market.get(key) or "") for key in keys).lower() for token in tokens)
    ]
