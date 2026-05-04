from app.intelligence.projection_engine import project_prop
from app.intelligence.query_engine import answer_query


def test_projection_contains_edge():
    result = project_prop({"sport": "NBA", "player": "A", "market": "Points", "line": 20, "recent": [22, 25, 19]})
    assert "edge" in result
    assert result["projection"] > 0


def test_query_returns_answer():
    result = answer_query("Is Brunson over 27.5 points worth researching?")
    assert "answer" in result
    assert result["projection"]["sport"] == "NBA"
