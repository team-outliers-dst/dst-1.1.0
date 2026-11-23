"""Coordinate raw input collection without fabricating unverifiable records."""

from __future__ import annotations

import pandas as pd
import requests

from . import config as project_config
from .config import RAW_DIR, ensure_directories, load_config
from .tmdb_collector import collect_tmdb, flatten_tmdb
from .youtube_collector import fetch_comments, fetch_video_statistics


def collect_all(refresh: bool = False) -> None:
    load_config()
    ensure_directories()
    master = pd.read_csv(RAW_DIR / "movie_master.csv")
    required = {"movie_id", "movie_name", "language", "release_date", "youtube_video_id"}
    missing = required.difference(master.columns)
    if missing:
        raise ValueError(f"movie_master.csv is missing required columns: {sorted(missing)}")
    tmdb_json = RAW_DIR / "tmdb_movies.json"
    if refresh or not tmdb_json.exists():
        payloads = collect_tmdb(master, api_key=project_config.TMDB_API_KEY)
        tmdb_rows = flatten_tmdb(payloads)
        tmdb_rows = tmdb_rows.rename(columns={"movie_id": "tmdb_id"})
        tmdb_rows["movie_id"] = master["movie_id"].values
        tmdb_rows["master_movie_name"] = master["movie_name"].values
        tmdb_rows["master_language"] = master["language"].values
        tmdb_rows["master_release_date"] = master["release_date"].values
        tmdb_rows.to_csv(RAW_DIR / "tmdb_movies.csv", index=False)
    verified = master.loc[
        master["youtube_video_id"].notna()
        & master["official_trailer_verified"].astype(str).str.lower().isin({"true", "yes", "1"}),
        "youtube_video_id",
    ].dropna().astype(str)
    if verified.empty:
        print("No manually verified YouTube video IDs found; skipping YouTube collection.")
        return
    stats = fetch_video_statistics(verified.tolist(), project_config.YOUTUBE_API_KEY)
    stats = stats.merge(
        master[["movie_id", "movie_name", "youtube_video_id", "youtube_channel", "official_trailer_verified"]],
        left_on="video_id",
        right_on="youtube_video_id",
        how="left",
    )
    stats.drop(columns=["youtube_video_id"], inplace=True)
    stats.to_csv(RAW_DIR / "youtube_stats.csv", index=False)
    comments = []
    for row in master.itertuples(index=False):
        if pd.isna(row.youtube_video_id):
            continue
        if str(getattr(row, "official_trailer_verified", "")).lower() not in {"true", "yes", "1"}:
            continue
        try:
            comments.append(
                fetch_comments(row.youtube_video_id, str(row.movie_id), project_config.YOUTUBE_API_KEY)
            )
        except requests.RequestException as exc:
            print(f"Comments unavailable for {row.movie_name}: {exc}")
    if comments:
        pd.concat(comments, ignore_index=True).to_csv(RAW_DIR / "youtube_comments.csv", index=False)


if __name__ == "__main__":
    collect_all()
