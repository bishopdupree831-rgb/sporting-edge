from __future__ import annotations

import html
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULTS = {"pending", "win", "loss", "push"}
SORTS = {"newest", "top", "most_discussed"}
VOTES = {"up", "down"}

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path("/tmp/sporting_edge_community.db") if os.getenv("RENDER") else BASE_DIR / "community.db"
DB_PATH = Path(os.getenv("COMMUNITY_DB_PATH", DEFAULT_DB))


def set_db_path(path: str | Path) -> None:
    global DB_PATH
    DB_PATH = Path(path)
    init_db()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any, limit: int = 240) -> str:
    text = html.escape(str(value or "").strip(), quote=True)
    return text[:limit]


def clean_tags(tags: Any) -> list[str]:
    if not isinstance(tags, list):
        return []
    return [clean_text(tag, 32).lower() for tag in tags if clean_text(tag, 32)][:8]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS community_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                sport TEXT NOT NULL,
                matchup TEXT NOT NULL,
                pick TEXT NOT NULL,
                odds INTEGER NOT NULL,
                sportsbook TEXT NOT NULL,
                market_type TEXT NOT NULL,
                confidence TEXT NOT NULL,
                units REAL NOT NULL,
                reasoning TEXT NOT NULL,
                tags TEXT NOT NULL,
                result TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS community_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES community_posts(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS community_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                vote TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(post_id, username),
                FOREIGN KEY(post_id) REFERENCES community_posts(id) ON DELETE CASCADE
            )
            """
        )


def odds_profit(units: float, odds: int) -> float:
    if odds > 0:
        return units * odds / 100
    return units * 100 / abs(odds)


def row_to_post(row: sqlite3.Row, comments: int = 0, upvotes: int = 0, downvotes: int = 0) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "sport": row["sport"],
        "matchup": row["matchup"],
        "pick": row["pick"],
        "odds": row["odds"],
        "sportsbook": row["sportsbook"],
        "market_type": row["market_type"],
        "confidence": row["confidence"],
        "units": row["units"],
        "reasoning": row["reasoning"],
        "tags": [tag for tag in row["tags"].split(",") if tag],
        "upvotes": upvotes,
        "downvotes": downvotes,
        "score": upvotes - downvotes,
        "comments_count": comments,
        "result": row["result"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def post_counts(conn: sqlite3.Connection) -> dict[int, dict[str, int]]:
    counts: dict[int, dict[str, int]] = {}
    for row in conn.execute("SELECT post_id, COUNT(*) count FROM community_comments GROUP BY post_id"):
        counts.setdefault(row["post_id"], {"comments": 0, "up": 0, "down": 0})["comments"] = row["count"]
    for row in conn.execute("SELECT post_id, vote, COUNT(*) count FROM community_votes GROUP BY post_id, vote"):
        counts.setdefault(row["post_id"], {"comments": 0, "up": 0, "down": 0})[row["vote"]] = row["count"]
    return counts


def create_post(payload: dict[str, Any]) -> dict[str, Any]:
    username = clean_text(payload.get("username") or "Guest", 40) or "Guest"
    sport = clean_text(payload.get("sport"), 12).upper()
    matchup = clean_text(payload.get("matchup"), 120)
    pick = clean_text(payload.get("pick"), 220)
    if not sport or not matchup or not pick:
        raise ValueError("sport, matchup, and pick are required")
    try:
        odds = int(payload.get("odds"))
    except (TypeError, ValueError):
        raise ValueError("odds must be a valid integer") from None
    if odds == 0:
        raise ValueError("odds cannot be zero")
    try:
        units = float(payload.get("units", 1.0))
    except (TypeError, ValueError):
        raise ValueError("units must be numeric") from None
    if units <= 0 or units > 100:
        raise ValueError("units must be between 0 and 100")
    now = utc_now()
    tags = ",".join(clean_tags(payload.get("tags")))
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO community_posts
            (username, sport, matchup, pick, odds, sportsbook, market_type, confidence, units, reasoning, tags, result, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                username,
                sport,
                matchup,
                pick,
                odds,
                clean_text(payload.get("sportsbook") or "Unknown", 80),
                clean_text(payload.get("market_type") or "Other", 60),
                clean_text(payload.get("confidence") or "C", 8),
                units,
                clean_text(payload.get("reasoning"), 1500),
                tags,
                now,
                now,
            ),
        )
        post_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,)).fetchone()
    return row_to_post(row)


def list_posts(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    clauses = []
    params: list[Any] = []
    if filters.get("sport"):
        clauses.append("sport = ?")
        params.append(str(filters["sport"]).upper())
    if filters.get("market_type"):
        clauses.append("market_type = ?")
        params.append(clean_text(filters["market_type"], 60))
    if filters.get("confidence"):
        clauses.append("confidence = ?")
        params.append(clean_text(filters["confidence"], 8))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sort = filters.get("sort", "newest")
    if sort not in SORTS:
        sort = "newest"
    with connect() as conn:
        counts = post_counts(conn)
        rows = conn.execute(f"SELECT * FROM community_posts {where}", params).fetchall()
    posts = []
    for row in rows:
        count = counts.get(row["id"], {"comments": 0, "up": 0, "down": 0})
        posts.append(row_to_post(row, count["comments"], count["up"], count["down"]))
    if sort == "top":
        posts.sort(key=lambda item: (item["score"], item["created_at"]), reverse=True)
    elif sort == "most_discussed":
        posts.sort(key=lambda item: (item["comments_count"], item["created_at"]), reverse=True)
    else:
        posts.sort(key=lambda item: item["created_at"], reverse=True)
    return {"posts": posts, "record": community_record(), "data_freshness": utc_now()}


def get_post(post_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise LookupError("post not found")
        counts = post_counts(conn).get(post_id, {"comments": 0, "up": 0, "down": 0})
        comments = [
            dict(comment)
            for comment in conn.execute(
                "SELECT id, post_id, username, comment, created_at FROM community_comments WHERE post_id = ? ORDER BY created_at ASC",
                (post_id,),
            )
        ]
    post = row_to_post(row, counts["comments"], counts["up"], counts["down"])
    post["comments"] = comments
    return post


def vote_post(post_id: int, username: str, vote: str) -> dict[str, Any]:
    username = clean_text(username or "Guest", 40) or "Guest"
    vote = clean_text(vote, 8).lower()
    if vote not in VOTES:
        raise ValueError("vote must be up or down")
    now = utc_now()
    with connect() as conn:
        exists = conn.execute("SELECT id FROM community_posts WHERE id = ?", (post_id,)).fetchone()
        if not exists:
            raise LookupError("post not found")
        conn.execute(
            """
            INSERT INTO community_votes (post_id, username, vote, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(post_id, username) DO UPDATE SET vote = excluded.vote, updated_at = excluded.updated_at
            """,
            (post_id, username, vote, now, now),
        )
    return get_post(post_id)


def add_comment(post_id: int, username: str, comment: str) -> dict[str, Any]:
    username = clean_text(username or "Guest", 40) or "Guest"
    comment = clean_text(comment, 600)
    if not comment:
        raise ValueError("comment is required")
    with connect() as conn:
        exists = conn.execute("SELECT id FROM community_posts WHERE id = ?", (post_id,)).fetchone()
        if not exists:
            raise LookupError("post not found")
        cursor = conn.execute(
            "INSERT INTO community_comments (post_id, username, comment, created_at) VALUES (?, ?, ?, ?)",
            (post_id, username, comment, utc_now()),
        )
        row = conn.execute("SELECT id, post_id, username, comment, created_at FROM community_comments WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def grade_post(post_id: int, result: str) -> dict[str, Any]:
    result = clean_text(result, 12).lower()
    if result not in RESULTS:
        raise ValueError("result must be pending, win, loss, or push")
    now = utc_now()
    with connect() as conn:
        cursor = conn.execute("UPDATE community_posts SET result = ?, updated_at = ? WHERE id = ?", (result, now, post_id))
        if cursor.rowcount == 0:
            raise LookupError("post not found")
    return get_post(post_id)


def community_record() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT result, units, odds FROM community_posts WHERE result != 'pending'").fetchall()
    wins = sum(1 for row in rows if row["result"] == "win")
    losses = sum(1 for row in rows if row["result"] == "loss")
    pushes = sum(1 for row in rows if row["result"] == "push")
    units = 0.0
    for row in rows:
        if row["result"] == "win":
            units += odds_profit(row["units"], row["odds"])
        elif row["result"] == "loss":
            units -= row["units"]
    return {"wins": wins, "losses": losses, "pushes": pushes, "units": round(units, 2), "label": f"{wins}-{losses}-{pushes}", "units_label": f"{units:+.1f} units"}


init_db()
