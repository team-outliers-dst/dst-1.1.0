"""Generate an evidence-based data inventory and source register."""

from __future__ import annotations

from pathlib import Path
from datetime import date

import pandas as pd


def generate_documentation(project_root: str | Path) -> None:
    root = Path(project_root)
    raw = root / "data" / "raw"
    cleaned = root / "data" / "cleaned"

    inventory_rows = []
    for file in sorted(list(raw.glob("*")) + list(cleaned.glob("*"))):
        if not file.is_file():
            continue
        row = {
            "dataset_name": file.name,
            "source": "TMDB / YouTube / Google Trends / starter template",
            "file_format": file.suffix.lstrip(".").upper() or "unknown",
            "number_of_records": "",
            "file_size_bytes": file.stat().st_size,
            "data_types": "",
        }
        if file.suffix.lower() == ".csv":
            frame = pd.read_csv(file)
            row["number_of_records"] = len(frame)
            row["data_types"] = "; ".join(
                f"{column}:{dtype}" for column, dtype in frame.dtypes.items()
            )
        inventory_rows.append(row)
    pd.DataFrame(inventory_rows).to_csv(
        raw / "data_inventory.csv", index=False
    )

    sources = [
        {
            "source_name": "The Movie Database (TMDB)",
            "source_url": "https://developer.themoviedb.org/docs",
            "data_format": "JSON/CSV",
            "fields_collected": "movie ID, title, genre, language, release date, runtime, rating, votes, cast",
            "collection_method": "TMDB API",
            "access_date": date.today().isoformat(),
            "terms_or_usage_notes": "API terms apply; credentials remain private.",
        },
        {
            "source_name": "YouTube Data API",
            "source_url": "https://developers.google.com/youtube/v3",
            "data_format": "JSON/CSV/text",
            "fields_collected": "trailer statistics and publicly accessible comments",
            "collection_method": "YouTube videos.list and commentThreads.list",
            "access_date": date.today().isoformat(),
            "terms_or_usage_notes": "YouTube API Terms and quota limits apply; comments remain public-source text.",
        },
        {
            "source_name": "Google Trends",
            "source_url": "https://trends.google.com/trends/",
            "data_format": "CSV",
            "fields_collected": "search interest (0-100)",
            "collection_method": "manual consistent India CSV export",
            "access_date": date.today().isoformat(),
            "terms_or_usage_notes": "Google Trends terms apply; relative, not absolute search volume.",
        },
        {
            "source_name": "IMDb 50K Reviews",
            "source_url": "https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews",
            "data_format": "CSV",
            "fields_collected": "general reviews and sentiment labels",
            "collection_method": "supplementary Kaggle download",
            "access_date": date.today().isoformat(),
            "terms_or_usage_notes": "Separate general movie-review corpus; not merged with selected films.",
        },
    ]
    pd.DataFrame(sources).to_csv(raw / "source_register.csv", index=False)
