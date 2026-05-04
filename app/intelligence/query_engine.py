from __future__ import annotations

from typing import Any

from app.intelligence.projection_engine import project_prop


def parse_query(text: str) -> dict[str, Any]:
    lower = text.lower()
    sport = "NBA"
    for candidate in ("NFL", "MLB", "NBA", "NHL", "MMA"):
        if candidate.lower() in lower:
            sport = candidate
            break
    market = "Points"
    for candidate in ("passing yards", "receiving yards", "rushing yards", "shots", "saves", "hits", "total bases", "takedowns", "points", "rebounds", "assists"):
        if candidate in lower:
            market = candidate.title()
            break
    line = 0.0
    for part in lower.replace("?", " ").split():
        try:
            line = float(part)
            break
        except ValueError:
            continue
    player = text.split(" over ")[0].replace("Is ", "").replace("is ", "").strip() or "Selected player"
    return {"sport": sport, "player": player, "market": market, "line": line or 24.5, "odds": -110}


def answer_query(text: str) -> dict[str, Any]:
    parsed = parse_query(text)
    projection = project_prop(parsed)
    verdict = "worth researching" if projection["edge"] > 0.03 else "not a clear edge yet"
    return {
        "query": text,
        "parsed": parsed,
        "answer": (
            f"{projection['player']} {projection['market']} is {verdict}. "
            f"The model projects {projection['projection']} against {projection['line']} with "
            f"{round(projection['confidence'] * 100)}% confidence."
        ),
        "projection": projection,
        "followups": [
            "Check injury and lineup status before placing anything.",
            "Compare best available odds across books.",
            "Review line movement for steam or reverse movement.",
        ],
    }
