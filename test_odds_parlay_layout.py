from odds_parlay_layout_engine import default_cards, layout_card


def test_default_cards_render():
    cards = default_cards("NBA")
    assert cards
    assert "legs" in cards[0]


def test_layout_card_has_badge():
    card = layout_card([{"player": "A", "market": "Points", "line": 20, "true_probability": 0.61, "odds": -110}])
    assert card["badge"] in {"premium", "playable", "watch"}
