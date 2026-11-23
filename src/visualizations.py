"""PNG visualisations generated from collected, cleaned data."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .config import VISUALIZATIONS_DIR


def _save(plotter, filename: str) -> None:
    VISUALIZATIONS_DIR.mkdir(parents=True, exist_ok=True)
    plotter()
    plt.tight_layout()
    plt.savefig(VISUALIZATIONS_DIR / filename, dpi=160)
    plt.close()


def generate_charts(movie_engagement: pd.DataFrame, comments: pd.DataFrame | None = None) -> None:
    sns.set_theme(style="whitegrid")
    if {"genre", "engagement_index"} <= set(movie_engagement.columns):
        def genre_plot() -> None:
            table = movie_engagement.groupby("genre", dropna=False)["engagement_index"].mean().sort_values()
            table.plot(kind="barh")
            plt.xlabel("Average project engagement index")
            plt.ylabel("Genre")
            plt.title("Genre vs Average Engagement")
        _save(genre_plot, "genre_vs_engagement.png")
    if {"language", "views_per_day"} <= set(movie_engagement.columns):
        def language_plot() -> None:
            table = movie_engagement.groupby("language", dropna=False)["views_per_day"].agg(["mean", "count"]).sort_index()
            ax = table["mean"].plot(kind="bar")
            ax.set_xlabel("Language")
            ax.set_ylabel("Average views per day")
            ax.set_title("Language vs Average Views per Day")
            for index, (value, count) in enumerate(zip(table["mean"], table["count"])):
                ax.text(index, value, f"n={count}", ha="center", va="bottom")
        _save(language_plot, "language_vs_views_per_day.png")
    if {"lead_cast_popularity", "views_per_day"} <= set(movie_engagement.columns):
        def cast_plot() -> None:
            ax = sns.scatterplot(data=movie_engagement, x="lead_cast_popularity", y="views_per_day", hue="movie_name")
            ax.set_xlabel("TMDB lead-cast popularity")
            ax.set_ylabel("Trailer views per day")
            ax.set_title("Cast Popularity vs Trailer Views")
        _save(cast_plot, "cast_vs_views.png")
    if {"tmdb_rating", "engagement_index"} <= set(movie_engagement.columns):
        def rating_plot() -> None:
            ax = sns.scatterplot(data=movie_engagement, x="tmdb_rating", y="engagement_index", hue="movie_name")
            ax.set_xlabel("TMDB rating")
            ax.set_ylabel("Project engagement index")
            ax.set_title("TMDB Rating vs Engagement")
        _save(rating_plot, "rating_vs_engagement.png")
    if {"average_search_interest", "engagement_index"} <= set(movie_engagement.columns):
        def trends_plot() -> None:
            ax = sns.scatterplot(
                data=movie_engagement,
                x="average_search_interest",
                y="engagement_index",
                hue="movie_name",
            )
            ax.set_xlabel("Average Google Trends interest (0-100)")
            ax.set_ylabel("Project engagement index")
            ax.set_title("Google Trends Interest vs Engagement")
        _save(trends_plot, "google_trends_vs_engagement.png")
    if comments is not None and {"topic", "sentiment"} <= set(comments.columns):
        def topic_plot() -> None:
            table = pd.crosstab(comments["topic"], comments["sentiment"])
            table.reindex(columns=["positive", "neutral", "negative"], fill_value=0).plot(kind="bar", stacked=True)
            plt.xlabel("Comment topic")
            plt.ylabel("Number of comments")
        _save(topic_plot, "comment_topics_vs_sentiment.png")
