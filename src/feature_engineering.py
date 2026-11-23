"""Derived engagement metrics."""

from __future__ import annotations

import pandas as pd


def _min_max(series: pd.Series) -> pd.Series:
    minimum, maximum = series.min(), series.max()
    if pd.isna(minimum) or maximum == minimum:
        return pd.Series(0.0, index=series.index)
    return (series - minimum) / (maximum - minimum)


def add_engagement_metrics(stats: pd.DataFrame) -> pd.DataFrame:
    result = stats.copy()
    published = pd.to_datetime(result["published_at"], errors="coerce", utc=True)
    retrieved = pd.to_datetime(result["retrieved_at"], errors="coerce", utc=True)
    days = (retrieved - published).dt.total_seconds().div(86400).clip(lower=1)
    result["days_since_publication"] = days
    result["views_per_day"] = result["views"].div(days).where(result["views"].notna())
    result["like_rate"] = result["likes"].div(result["views"]).mul(100).where(result["views"].gt(0))
    result["comment_rate"] = result["comment_count"].div(result["views"]).mul(100).where(result["views"].gt(0))
    result["normalized_views_per_day"] = _min_max(result["views_per_day"])
    result["normalized_like_rate"] = _min_max(result["like_rate"])
    result["normalized_comment_rate"] = _min_max(result["comment_rate"])
    result["engagement_index"] = (
        0.50 * result["normalized_views_per_day"]
        + 0.25 * result["normalized_like_rate"]
        + 0.25 * result["normalized_comment_rate"]
    )
    return result
