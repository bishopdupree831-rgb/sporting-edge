from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

NEWS_BASE_URL = "https://newsapi.org/v2/everything"


def news_key() -> str:
    return os.getenv("NEWS_API_KEY", "").strip()


def news_status() -> dict:
    connected = bool(news_key())
    return {
        "name": "news_provider",
        "env_var": "NEWS_API_KEY",
        "connected": connected,
        "source": "NewsAPI" if connected else "not connected",
        "freshness": datetime.now(timezone.utc).isoformat(),
    }


def fetch_news(query: str, page_size: int = 20) -> dict[str, Any]:
    key = news_key()
    if not key:
        raise RuntimeError("Live provider not connected. Real-time mode unavailable.")
    response = requests.get(
        NEWS_BASE_URL,
        params={
            "apiKey": key,
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(max(page_size, 1), 50),
        },
        timeout=10,
    )
    response.raise_for_status()
    return {
        "articles": response.json().get("articles", []),
        "meta": {"source": "NewsAPI", "last_updated": datetime.now(timezone.utc).isoformat()},
        "provider": news_status(),
    }
