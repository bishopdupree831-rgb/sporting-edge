from app.simulator_engine import analyze_betslip, build_edge_score, build_parlay


def test_edge_score_positive_candidate():
    result = build_edge_score({"true_probability": 0.62, "odds": -110, "projection": 28, "line": 25})
    assert result["edge"] > 0
    assert result["ev"] > 0
    assert result["confidence"] > 0.5


def test_parlay_has_requested_legs():
    legs = [
        {"player": "A", "market": "Points", "true_probability": 0.62, "odds": -110},
        {"player": "B", "market": "Rebounds", "true_probability": 0.59, "odds": -105},
        {"player": "C", "market": "Assists", "true_probability": 0.6, "odds": 100},
    ]
    result = build_parlay(legs, target_legs=2)
    assert len(result["legs"]) == 2
    assert result["combined_probability"] > 0


def test_betslip_analyzer_flags_risk():
    result = analyze_betslip([{"true_probability": 0.52, "odds": -130}, {"true_probability": 0.51, "odds": -120}])
    assert "risk_flags" in result
