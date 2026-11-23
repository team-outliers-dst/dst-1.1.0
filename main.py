"""Run the Release Day Radar pipeline using available raw inputs."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.config import CLEANED_DIR, RAW_DIR, ensure_directories, load_config
from src.data_cleaning import clean_raw_files
from src.feature_engineering import add_engagement_metrics
from src.sentiment_analysis import analyse_comments
from src.exploratory_analysis import summaries
from src.visualizations import generate_charts
from src.database import create_schema, load_cleaned_data
from src.data_inventory import generate_documentation
from src.google_trends_analysis import run as run_google_trends


ROOT = Path(__file__).resolve().parent


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_config()
    ensure_directories()
    generate_documentation(ROOT)
    clean_raw_files()
    batch_files = [
        RAW_DIR / "batch1_time_series.csv",
        RAW_DIR / "batch2_time_series.csv",
        RAW_DIR / "batch1_by_region.csv",
        RAW_DIR / "batch2_by_region.csv",
    ]
    if all(path.exists() for path in batch_files):
        run_google_trends(RAW_DIR)
        logging.info("Google Trends batch alignment, regional analysis, and charts completed.")
    stats_path = CLEANED_DIR / "cleaned_stats.csv"
    comments_path = CLEANED_DIR / "cleaned_comments.csv"
    if not stats_path.exists():
        logging.warning("No cleaned YouTube statistics found; add raw/youtube_stats.csv and rerun.")
        return
    stats = add_engagement_metrics(pd.read_csv(stats_path))
    tmdb_path = RAW_DIR / "tmdb_movies.csv"
    if tmdb_path.exists():
        tmdb = pd.read_csv(tmdb_path, encoding="utf-8")
        tmdb_key = pd.DataFrame({
            "movie_id": tmdb["movie_id"],
            "tmdb_id": tmdb["tmdb_id"],
            "movie_name": tmdb["master_movie_name"].where(
                tmdb["master_movie_name"].notna(), tmdb["movie_name"]
            ),
            "language": tmdb["master_language"].where(
                tmdb["master_language"].notna(), tmdb["language"]
            ),
            "genre": tmdb["genre"],
            "runtime_minutes": tmdb["runtime_minutes"],
            "lead_cast_popularity": tmdb["lead_cast_popularity"],
            "tmdb_rating": tmdb["tmdb_rating"],
            "tmdb_vote_count": tmdb["tmdb_vote_count"],
        })
        stats = stats.merge(tmdb_key, on="movie_id", how="left")
    if "movie_name_x" in stats.columns or "movie_name_y" in stats.columns:
        stats["movie_name"] = stats["movie_name_x"].combine_first(
            stats["movie_name_y"]
        )
        stats.drop(
            columns=["movie_name_x", "movie_name_y"],
            inplace=True,
            errors="ignore",
        )
    trends_path = CLEANED_DIR / "cleaned_google_trends.csv"
    if trends_path.exists():
        trends = pd.read_csv(trends_path)
        trend_summary = (
            trends.groupby("movie_id", dropna=False)["search_interest_0_100"]
            .mean()
            .rename("average_search_interest")
            .reset_index()
        )
        stats = stats.merge(trend_summary, on="movie_id", how="left")
    stats.to_csv(CLEANED_DIR / "movie_engagement.csv", index=False)
    for name, frame in summaries(stats).items():
        frame.to_csv(CLEANED_DIR / f"{name}.csv", index=False)
    comments = None
    if comments_path.exists():
        comments = analyse_comments(pd.read_csv(comments_path))
        comments.to_csv(CLEANED_DIR / "analysed_comments.csv", index=False)
    generate_charts(stats, comments)
    try:
        create_schema(ROOT / "sql" / "schema.sql")
        analysed_comments = CLEANED_DIR / "analysed_comments.csv"
        load_cleaned_data(
            CLEANED_DIR / "movie_engagement.csv",
            analysed_comments if analysed_comments.exists() else comments_path,
        )
        logging.info("MySQL schema and cleaned data loaded successfully.")
    except Exception as exc:
        logging.warning("MySQL loading skipped or incomplete: %s", exc)
    logging.info("Pipeline completed with available data. Raw files were not modified.")


if __name__ == "__main__":
    main()
