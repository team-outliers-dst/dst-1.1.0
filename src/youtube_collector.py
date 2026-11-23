"""YouTube trailer statistics and comment collection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from .config import RAW_DIR, YOUTUBE_API_KEY

API_URL = "https://www.googleapis.com/youtube/v3"


def _request(resource: str, params: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY is not configured.")
    response = requests.get(f"{API_URL}/{resource}", params={**params, "key": api_key}, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_video_statistics(video_ids: list[str], api_key: str | None = None) -> pd.DataFrame:
    """Retrieve statistics only for manually verified video IDs."""
    api_key = api_key or YOUTUBE_API_KEY
    if not video_ids:
        return pd.DataFrame()
    payload = _request(
        "videos",
        {"part": "snippet,statistics,contentDetails", "id": ",".join(video_ids)},
        api_key,
    )
    retrieved_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for item in payload.get("items", []):
        snippet, stats = item.get("snippet", {}), item.get("statistics", {})
        rows.append(
            {
                "video_id": item["id"],
                "video_title": snippet.get("title"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "views": stats.get("viewCount"),
                "likes": stats.get("likeCount"),
                "comment_count": stats.get("commentCount"),
                "duration": item.get("contentDetails", {}).get("duration"),
                "retrieved_at": retrieved_at,
            }
        )
    return pd.DataFrame(rows)


def fetch_comments(
    video_id: str,
    movie_id: str,
    api_key: str | None = None,
    max_comments: int = 1000,
) -> pd.DataFrame:
    api_key = api_key or YOUTUBE_API_KEY
    rows: list[dict[str, Any]] = []
    page_token = None
    while True:
        params: dict[str, Any] = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 100,
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token
        payload = _request("commentThreads", params, api_key)
        for item in payload.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            rows.append(
                {
                    "comment_id": item["snippet"]["topLevelComment"]["id"],
                    "movie_id": movie_id,
                    "video_id": video_id,
                    "comment_text": snippet.get("textDisplay"),
                    "published_at": snippet.get("publishedAt"),
                    "like_count": snippet.get("likeCount"),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            if len(rows) >= max_comments:
                break
        if len(rows) >= max_comments:
            break
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return pd.DataFrame(rows)
