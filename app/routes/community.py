from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.community import add_comment, create_post, get_post, grade_post, list_posts, vote_post

router = APIRouter(tags=["community-picks"])


class CommunityPostRequest(BaseModel):
    username: str = "Guest"
    sport: str
    matchup: str
    pick: str
    odds: int
    sportsbook: str = "Unknown"
    market_type: str = "Player Prop"
    confidence: str = "C"
    units: float = Field(1.0, gt=0, le=100)
    reasoning: str = Field("", max_length=1500)
    tags: list[str] = Field(default_factory=list)


class VoteRequest(BaseModel):
    username: str = "Guest"
    vote: str


class CommentRequest(BaseModel):
    username: str = "Guest"
    comment: str = Field(..., min_length=1, max_length=600)


class GradeRequest(BaseModel):
    result: str


@router.post("/api/community/posts")
def create_community_post(payload: CommunityPostRequest) -> dict[str, Any]:
    try:
        return create_post(payload.dict())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/community/posts")
def get_community_posts(
    sport: str | None = None,
    market_type: str | None = None,
    confidence: str | None = None,
    sort: str = Query("newest", pattern="^(newest|top|most_discussed)$"),
) -> dict[str, Any]:
    return list_posts({"sport": sport, "market_type": market_type, "confidence": confidence, "sort": sort})


@router.get("/api/community/posts/{post_id}")
def get_community_post(post_id: int) -> dict[str, Any]:
    try:
        return get_post(post_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/community/posts/{post_id}/vote")
def vote_community_post(post_id: int, payload: VoteRequest) -> dict[str, Any]:
    try:
        return vote_post(post_id, payload.username, payload.vote)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/community/posts/{post_id}/comments")
def comment_community_post(post_id: int, payload: CommentRequest) -> dict[str, Any]:
    try:
        return add_comment(post_id, payload.username, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/community/posts/{post_id}/grade")
def grade_community_post(post_id: int, payload: GradeRequest) -> dict[str, Any]:
    try:
        return grade_post(post_id, payload.result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
