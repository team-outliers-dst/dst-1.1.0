"""TMDB metadata collection with raw-response preservation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .config import RAW_DIR, TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"


def fetch_movie(
    movie_name: str,
    api_key: str | None = None,
    release_date: str | None = None,
) -> dict[str, Any]:
    api_key = api_key or TMDB_API_KEY
    if not api_key:
        raise RuntimeError("TMDB_API_KEY is not configured.")
    params: dict[str, Any] = {"api_key": api_key, "query": movie_name, "include_adult": "false"}
    if release_date:
        params["primary_release_year"] = release_date[:4]
    response = requests.get(
        f"{BASE_URL}/search/movie",
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise LookupError(f"TMDB returned no result for {movie_name!r}.")
    movie_id = results[0]["id"]
    details = requests.get(
        f"{BASE_URL}/movie/{movie_id}",
        params={"api_key": api_key, "append_to_response": "credits"},
        timeout=30,
    )
    details.raise_for_status()
    return details.json()


def collect_tmdb(
    movie_master: pd.DataFrame,
    output_path: Path | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch each title and save the unchanged API payload as JSON."""
    payloads: list[dict[str, Any]] = []
    for row in movie_master.itertuples(index=False):
        payloads.append(
            fetch_movie(
                str(row.movie_name),
                api_key,
                str(row.release_date) if hasattr(row, "release_date") else None,
            )
        )
    output_path = output_path or RAW_DIR / "tmdb_movies.json"
    output_path.write_text(
        json.dumps(
            {"retrieved_at": datetime.now(timezone.utc).isoformat(), "movies": payloads},
            indent=2,
        ),
        encoding="utf-8",
    )
    return payloads


def flatten_tmdb(payloads: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for movie in payloads:
        cast = movie.get("credits", {}).get("cast", [])[:5]
        rows.append(
            {
                "movie_id": movie.get("id"),
                "movie_name": movie.get("title"),
                "genre": ", ".join(item["name"] for item in movie.get("genres", [])),
                "language": movie.get("original_language"),
                "runtime_minutes": movie.get("runtime"),
                "cast_names": ", ".join(item.get("name", "") for item in cast),
                "lead_cast_popularity": max((item.get("popularity", 0) for item in cast), default=None),
                "tmdb_rating": movie.get("vote_average"),
                "tmdb_vote_count": movie.get("vote_count"),
                "tmdb_popularity": movie.get("popularity"),
                "release_date": movie.get("release_date"),
                "tmdb_source_url": f"https://www.themoviedb.org/movie/{movie.get('id')}",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return pd.json_normalize(rows)
