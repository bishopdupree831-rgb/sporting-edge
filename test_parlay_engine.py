from app.services.parlay_engine import SAMPLE_BOARD, alt_ladder, analyze_slip, build_parlays


def test_sample_board_analyzes():
    result = analyze_slip(SAMPLE_BOARD[:3])
    assert len(result["legs"]) == 3
    assert result["slip"]["score"] > 0


def test_build_parlays_returns_cards():
    result = build_parlays(SAMPLE_BOARD)
    assert "balanced" in result
    assert len(result["balanced"]["legs"]) >= 2


def test_alt_ladder_steps():
    result = alt_ladder(SAMPLE_BOARD[0])
    assert len(result["ladder"]) == 5
    assert all("model_probability" in row for row in result["ladder"])
