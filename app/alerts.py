from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ALERTS: list[dict[str, Any]] = []


def create_alert(payload: dict[str, Any]) -> dict[str, Any]:
    alert_type = str(payload.get("type", "value_bet"))
    if alert_type not in {"value_bet", "line_move", "injury_news", "arbitrage", "clv"}:
        raise ValueError("unsupported alert type")
    row = {
        "id": len(ALERTS) + 1,
        "type": alert_type,
        "target": payload.get("target", "manual target"),
        "condition": payload.get("condition", "notify when triggered"),
        "threshold": payload.get("threshold"),
        "active": bool(payload.get("active", True)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    ALERTS.append(row)
    return row


def list_alerts() -> dict[str, Any]:
    return {"alerts": ALERTS, "data_freshness": datetime.now(timezone.utc).isoformat()}
