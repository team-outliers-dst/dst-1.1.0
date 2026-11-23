"""Descriptive analysis helpers that never manufacture missing findings."""

from __future__ import annotations

import pandas as pd


def summaries(movie_engagement: pd.DataFrame) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    if "genre" in movie_engagement and "engagement_index" in movie_engagement:
        result["genre_engagement"] = movie_engagement.groupby("genre", dropna=False)["engagement_index"].mean().reset_index()
    if "language" in movie_engagement and "views_per_day" in movie_engagement:
        result["language_views_per_day"] = movie_engagement.groupby("language", dropna=False)["views_per_day"].agg(["mean", "count"]).reset_index()
    numeric = movie_engagement.select_dtypes("number")
    result["correlations"] = numeric.corr() if not numeric.empty else pd.DataFrame()
    return result
