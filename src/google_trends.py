"""Load manually exported Google Trends data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "date",
    "movie_id",
    "movie_name",
    "search_term",
    "geo",
    "search_interest_0_100",
    "timeframe",
    "source",
}


def load_google_trends(input_path: str | Path) -> pd.DataFrame:
    """Clean a consistent Google Trends export without interpolating missing values."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Google Trends export not found: {path}. "
            "Export data first or leave the file absent to run without Trends."
        )
    trends = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(trends.columns)
    if missing:
        raise ValueError(
            f"Google Trends data is missing required columns: {sorted(missing)}"
        )
    trends["date"] = pd.to_datetime(trends["date"], errors="coerce")
    trends["search_interest_0_100"] = pd.to_numeric(
        trends["search_interest_0_100"], errors="coerce"
    )
    trends["geo"] = trends["geo"].str.upper().str.strip()
    trends["movie_name"] = trends["movie_name"].str.strip()
    trends = trends.drop_duplicates(
        subset=["date", "movie_id", "search_term", "geo", "timeframe"]
    )
    return trends
