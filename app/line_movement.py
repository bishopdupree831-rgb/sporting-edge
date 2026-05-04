from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def track_line_movement(payload: dict[str, Any]) -> dict[str, Any]:
    opening = float(payload.get("opening_line"))
    current = float(payload.get("current_line"))
    history = payload.get("line_history") or [opening, current]
    bet_pct = float(payload.get("public_betting_percentage", 50))
    money_pct = float(payload.get("public_money_percentage", bet_pct))
    direction = "up" if current > opening else "down" if current < opening else "flat"
    delta = current - opening
    steam = abs(delta) >= float(payload.get("steam_threshold", 1.0))
    public_side = "over/favorite" if bet_pct >= 55 else "under/dog" if bet_pct <= 45 else "balanced"
    reverse = (bet_pct >= 65 and delta < 0) or (bet_pct <= 35 and delta > 0)
    sharp_signal = "strong" if reverse or (steam and abs(money_pct - bet_pct) >= 15) else "watch" if steam else "none"
    return {
        "opening_line": opening,
        "current_line": current,
        "line_history": history,
        "movement": round(delta, 3),
        "direction": direction,
        "steam_move": steam,
        "reverse_line_movement": reverse,
        "public_side": public_side,
        "sharp_signal": sharp_signal,
        "verdict": "Reverse line movement detected; compare books and news before acting." if reverse else "Line movement logged.",
        "data_freshness": datetime.now(timezone.utc).isoformat(),
    }
