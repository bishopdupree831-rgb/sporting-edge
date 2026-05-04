from app.live_simulator import simulate


def test_live_simulator_manual_mode():
    result = simulate({
        "sport": "NBA",
        "matchup": "NYK vs IND",
        "market_type": "player_prop",
        "player_name": "Jalen Brunson",
        "stat_type": "assists",
        "line": 6.5,
        "odds": -110,
        "simulations": 10000,
        "live_context": {
            "season_average": 6.2,
            "last_5_average": 7.1,
            "last_10_average": 6.8,
            "opponent_average_allowed": 7.0,
        },
    })
    assert result["simulations"] == 10000
    assert "out of 10,000 simulations" in result["result_sentence"]
    assert "provider_sources" in result


def test_live_simulator_caps_trials():
    result = simulate({"sport": "NFL", "market_type": "total", "line": 44.5, "odds": -105, "simulations": 200000})
    assert result["simulations"] == 100000
