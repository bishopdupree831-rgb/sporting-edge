from pathlib import Path

from fastapi.testclient import TestClient

from main import app


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_homepage_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Sporting Edge" in response.text or "EdgeLab" in response.text


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_static_files_exist():
    required = [
        "static/theme.css",
        "static/dashboard.css",
        "static/sport_pages.css",
        "static/player_cards.css",
        "static/team_assets.js",
        "static/player_assets.js",
        "static/dashboard_layout.js",
    ]
    for path in required:
        assert (ROOT / path).exists(), path


def test_markets_missing_provider_state(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.delenv("OPTICODDS_API_KEY", raising=False)
    monkeypatch.delenv("SPORTSGAMEODDS_API_KEY", raising=False)
    monkeypatch.delenv("SPORTS_GAME_ODDS_KEY", raising=False)
    response = client.get("/api/markets?sport=NBA&sportsbook=DraftKings")
    assert response.status_code == 200
    payload = response.json()
    assert "markets" in payload
    assert payload["message"] in {
        "Live sportsbook provider not connected.",
        "Using cached data due to API limits",
    }


def test_existing_simulator_route_still_works():
    response = client.post(
        "/api/live-simulate",
        json={
            "sport": "NBA",
            "matchup": "Knicks vs Hawks",
            "market_type": "player_prop",
            "player_name": "Jalen Brunson",
            "stat_type": "assists",
            "line": 6.5,
            "odds": -110,
            "sportsbook": "DraftKings",
            "simulations": 1000,
            "live_context": {"season_average": 6.2, "last_5_average": 7.1},
        },
    )
    assert response.status_code == 200
    assert "simulations" in response.json()


def test_community_route_still_loads():
    response = client.get("/api/community/posts")
    assert response.status_code == 200
