"""MySQL schema loading for cleaned datasets."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pandas as pd

from .config import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER


def create_schema(schema_path: str | Path) -> None:
    try:
        import mysql.connector
    except ImportError as exc:
        raise RuntimeError("Install mysql-connector-python to use the database module.") from exc
    connection = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD
    )
    try:
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}`")
        cursor.execute(f"USE `{MYSQL_DATABASE}`")
        statements = Path(schema_path).read_text(encoding="utf-8").split(";")
        for statement in statements:
            if statement.strip():
                cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()


def load_cleaned_data(
    movie_engagement_path: str | Path,
    comments_path: str | Path | None = None,
) -> None:
    """Create tables and insert available cleaned movie, trailer, and comment rows."""
    try:
        import mysql.connector
    except ImportError as exc:
        raise RuntimeError("Install mysql-connector-python to use MySQL loading.") from exc

    engagement = pd.read_csv(movie_engagement_path)
    comments = pd.DataFrame()
    if comments_path and Path(comments_path).exists():
        comments = pd.read_csv(comments_path)

    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )
    try:
        cursor = connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("DELETE FROM comments")
        cursor.execute("DELETE FROM trailer_stats")
        cursor.execute("DELETE FROM films")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        for row in engagement.itertuples(index=False):
            movie_id = str(row.movie_id)
            cursor.execute(
                """
                INSERT INTO films (
                    movie_id, movie_name, language, genre, release_date, runtime,
                    cast_popularity, tmdb_rating, vote_count
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    movie_id,
                    getattr(row, "movie_name", None),
                    getattr(row, "language", None),
                    getattr(row, "genre", None),
                    pd.Timestamp(getattr(row, "release_date", None)).date()
                    if pd.notna(getattr(row, "release_date", None))
                    else None,
                    int(getattr(row, "runtime_minutes", 0))
                    if pd.notna(getattr(row, "runtime_minutes", None))
                    else None,
                    float(getattr(row, "lead_cast_popularity", 0))
                    if pd.notna(getattr(row, "lead_cast_popularity", None))
                    else None,
                    float(getattr(row, "tmdb_rating", 0))
                    if pd.notna(getattr(row, "tmdb_rating", None))
                    else None,
                    int(getattr(row, "tmdb_vote_count", 0))
                    if pd.notna(getattr(row, "tmdb_vote_count", None))
                    else None,
                ),
            )
            published = getattr(row, "published_at", None)
            cursor.execute(
                """
                INSERT INTO trailer_stats (
                    video_id, movie_id, views, likes, comment_count, published_at,
                    views_per_day, like_rate, comment_rate
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    getattr(row, "video_id", None),
                    movie_id,
                    int(getattr(row, "views", 0))
                    if pd.notna(getattr(row, "views", None))
                    else None,
                    int(getattr(row, "likes", 0))
                    if pd.notna(getattr(row, "likes", None))
                    else None,
                    int(getattr(row, "comment_count", 0))
                    if pd.notna(getattr(row, "comment_count", None))
                    else None,
                    pd.Timestamp(published).to_pydatetime()
                    if pd.notna(published)
                    else None,
                    float(getattr(row, "views_per_day", 0))
                    if pd.notna(getattr(row, "views_per_day", None))
                    else None,
                    float(getattr(row, "like_rate", 0))
                    if pd.notna(getattr(row, "like_rate", None))
                    else None,
                    float(getattr(row, "comment_rate", 0))
                    if pd.notna(getattr(row, "comment_rate", None))
                    else None,
                ),
            )

        if not comments.empty:
            for row in comments.itertuples(index=False):
                cursor.execute(
                    """
                    INSERT IGNORE INTO comments (
                        comment_id, movie_id, video_id, comment_text,
                        sentiment, sentiment_score, topic
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        str(row.comment_id),
                        str(row.movie_id),
                        str(row.video_id),
                        getattr(row, "comment_text", None),
                        getattr(row, "sentiment", None),
                        float(getattr(row, "sentiment_score", 0))
                        if pd.notna(getattr(row, "sentiment_score", None))
                        else None,
                        getattr(row, "topic", None),
                    ),
                )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    from .config import load_config, ROOT_DIR

    load_config()
    create_schema(ROOT_DIR / "sql" / "schema.sql")
    cleaned = ROOT_DIR / "data" / "cleaned"
    analysed = cleaned / "analysed_comments.csv"
    load_cleaned_data(
        cleaned / "movie_engagement.csv",
        analysed if analysed.exists() else cleaned / "cleaned_comments.csv",
    )
