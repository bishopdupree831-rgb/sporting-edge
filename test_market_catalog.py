from app.market_catalog import filter_markets, normalize_odds_api_events, search_markets


def sample_event(market_key, outcome, book="DraftKings", sport_key="basketball_nba"):
    return [{
        "id": "evt_1",
        "sport_key": sport_key,
        "home_team": "Atlanta Hawks",
        "away_team": "New York Knicks",
        "commence_time": "2026-05-04T23:00:00Z",
        "bookmakers": [{
            "key": book.lower(),
            "title": book,
            "last_update": "2026-05-04T20:00:00Z",
            "markets": [{
                "key": market_key,
                "last_update": "2026-05-04T20:01:00Z",
                "outcomes": [outcome],
            }],
        }],
    }]


def test_market_normalization_nba_player_prop():
    events = sample_event("player_assists", {"name": "Over", "description": "Jalen Brunson", "point": 6.5, "price": -115})
    markets = normalize_odds_api_events(events, "NBA", sportsbook="DraftKings")
    assert markets[0]["sportsbook"] == "DraftKings"
    assert markets[0]["market_group"] == "player assists"
    assert markets[0]["selection"] == "Jalen Brunson over 6.5 player assists"
    assert markets[0]["side"] == "over"


def test_nba_prop_search():
    markets = normalize_odds_api_events(
        sample_event("player_assists", {"name": "Over", "description": "Jalen Brunson", "point": 6.5, "price": -115}),
        "NBA",
    )
    assert search_markets(markets, "brunson assists")


def test_nfl_touchdown_prop():
    events = sample_event("player_anytime_td", {"name": "Yes", "description": "CeeDee Lamb", "price": 145}, sport_key="americanfootball_nfl")
    markets = normalize_odds_api_events(events, "NFL")
    assert markets[0]["market_group"] == "anytime touchdown"
    assert markets[0]["market_type"] == "player_prop"


def test_mlb_pitcher_strikeout_prop():
    events = sample_event("pitcher_strikeouts", {"name": "Over", "description": "Tarik Skubal", "point": 7.5, "price": -105}, sport_key="baseball_mlb")
    markets = normalize_odds_api_events(events, "MLB")
    assert markets[0]["market_group"] == "pitcher strikeouts"


def test_nhl_shots_prop():
    events = sample_event("player_shots_on_goal", {"name": "Over", "description": "Auston Matthews", "point": 3.5, "price": -120}, sport_key="icehockey_nhl")
    markets = normalize_odds_api_events(events, "NHL")
    assert markets[0]["market_group"] == "player shots on goal"


def test_mma_method_prop():
    events = sample_event("method_of_victory", {"name": "Submission", "description": "Islam Makhachev", "price": 225}, sport_key="mma_mixed_martial_arts")
    markets = normalize_odds_api_events(events, "MMA")
    assert markets[0]["market_group"] == "method of victory"
    assert markets[0]["market_type"] == "fighter_prop"


def test_filter_by_sportsbook_rejects_other_books():
    events = sample_event("h2h", {"name": "Atlanta Hawks", "price": -110}, book="OtherBook")
    assert normalize_odds_api_events(events, "NBA") == []


def test_filter_markets_by_team():
    events = sample_event("h2h", {"name": "Atlanta Hawks", "price": -110})
    markets = normalize_odds_api_events(events, "NBA")
    assert filter_markets(markets, team="Hawks")
