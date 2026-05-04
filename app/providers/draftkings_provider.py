from __future__ import annotations

import os
from typing import Any


BOOK_NAME = "DraftKings"


def affiliate_link() -> str | None:
    return os.getenv("DRAFTKINGS_AFFILIATE_LINK", "").strip() or None


def matches_bookmaker(bookmaker: dict[str, Any] | str | None) -> bool:
    if isinstance(bookmaker, dict):
        value = f"{bookmaker.get('title', '')} {bookmaker.get('key', '')}".lower()
    else:
        value = str(bookmaker or "").lower()
    return "draftkings" in value or value.strip() in {"dk", "draft_kings"}


def deep_link_for_market(market: dict[str, Any]) -> str | None:
    base = affiliate_link()
    if not base:
        return None
    event_id = str(market.get("event_id") or "").strip()
    if not event_id:
        return base
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}event_id={event_id}"
