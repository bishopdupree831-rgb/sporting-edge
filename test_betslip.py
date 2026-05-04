from app.betslip import analyze_betslip, create_betslip, export_betslip, send_to_book


def legs():
    return [
        {
            "sport": "NBA",
            "sportsbook": "DraftKings",
            "event_id": "evt_1",
            "game": "Knicks vs Hawks",
            "market_group": "player assists",
            "selection": "Jalen Brunson over 6.5 assists",
            "player_name": "Jalen Brunson",
            "side": "over",
            "line": 6.5,
            "odds": -115,
            "model_probability": 0.61,
        },
        {
            "sport": "NBA",
            "sportsbook": "DraftKings",
            "event_id": "evt_2",
            "game": "Celtics vs Heat",
            "market_group": "player threes",
            "selection": "Jayson Tatum over 2.5 threes",
            "player_name": "Jayson Tatum",
            "side": "over",
            "line": 2.5,
            "odds": 120,
            "model_probability": 0.52,
        },
    ]


def test_betslip_creation_and_parlay_odds():
    slip = create_betslip(legs(), stake=10)
    assert slip["combined_decimal_odds"] > 3
    assert slip["combined_odds"].startswith("+")
    assert slip["implied_probability"] > 0


def test_betslip_ev_and_edge_score():
    slip = analyze_betslip(legs(), stake=10)
    assert slip["model_probability"] > 0
    assert slip["edge_score"] is not None
    assert "verdict" in slip


def test_conflicting_leg_detection():
    conflict_legs = legs()
    conflict_legs.append({
        **conflict_legs[0],
        "selection": "Jalen Brunson under 6.5 assists",
        "side": "under",
        "odds": -105,
    })
    slip = analyze_betslip(conflict_legs)
    assert any("Conflicting" in warning for warning in slip["warnings"])


def test_export_slip_formats():
    exported = export_betslip(legs())
    assert "Sporting Edge Betslip" in exported["plain_text"]
    assert "json_betslip" in exported
    assert "csv_row" in exported


def test_blocked_unsafe_sportsbook_transfer(monkeypatch):
    monkeypatch.delenv("SHARPSPORTS_API_KEY", raising=False)
    response = send_to_book(legs(), sportsbook="DraftKings")
    assert response["ok"] is False
    assert response["message"] == "Direct sportsbook connection not available. Use copy betslip."


def test_invalid_empty_betslip():
    try:
        create_betslip([])
    except ValueError:
        return
    raise AssertionError("empty betslip should raise ValueError")
