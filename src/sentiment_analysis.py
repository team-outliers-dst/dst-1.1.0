"""VADER sentiment and transparent keyword topics."""

from __future__ import annotations

import pandas as pd

TOPIC_KEYWORDS = {
    "Acting": {"acting", "actor", "actress", "performance", "dialogue"},
    "Music": {"music", "song", "songs", "background", "soundtrack"},
    "Visuals": {"visual", "visuals", "cinematography", "vfx", "graphics"},
    "Story": {"story", "plot", "screenplay", "writing", "ending"},
    "Direction": {"director", "direction", "filmmaking"},
}


def classify_topic(text: str) -> str:
    words = set(str(text).lower().split())
    for topic, keywords in TOPIC_KEYWORDS.items():
        if words.intersection(keywords):
            return topic
    return "General"


def analyse_comments(comments: pd.DataFrame) -> pd.DataFrame:
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    except ImportError as exc:
        raise RuntimeError("Install vaderSentiment to run sentiment analysis.") from exc
    result = comments.copy()
    analyzer = SentimentIntensityAnalyzer()
    scores = result["comment_text"].fillna("").map(analyzer.polarity_scores)
    result["sentiment_score"] = scores.map(lambda item: item["compound"])
    result["sentiment"] = result["sentiment_score"].map(
        lambda value: "positive" if value >= 0.05 else "negative" if value <= -0.05 else "neutral"
    )
    result["topic"] = result["comment_text"].fillna("").map(classify_topic)
    return result
