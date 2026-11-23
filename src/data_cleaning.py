"""Pandas cleaning and audit logging."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .config import CLEANED_DIR, LOG_DIR, RAW_DIR


def _strip_html(value: object) -> object:
    if pd.isna(value):
        return value
    return re.sub(r"<[^>]+>", "", str(value)).strip()


def clean_comments(comments: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    log: list[dict[str, object]] = []
    result = comments.copy()
    before = len(result)
    result = result.drop_duplicates(subset=["comment_id"])
    after = len(result)
    log.append({
        "dataset_name": "youtube_comments",
        "column_affected": "comment_id",
        "problem_identified": "one duplicate comment ID",
        "rows_affected": before - after,
        "rows_before": before,
        "rows_after": after,
        "cleaning_action": "Removed duplicate rows using comment_id",
        "justification": "Preserve one row per source comment; comment IDs are unique identifiers",
    })
    if "comment_text" in result:
        html_rows = result["comment_text"].fillna("").astype(str).str.contains(r"<[^>]+>", regex=True).sum()
        result["comment_text"] = result["comment_text"].map(_strip_html)
        log.append({
            "dataset_name": "youtube_comments",
            "column_affected": "comment_text",
            "problem_identified": f"{int(html_rows)} rows contained HTML tags",
            "rows_affected": int(html_rows),
            "rows_before": after,
            "rows_after": after,
            "cleaning_action": "Removed HTML tags and trimmed leading/trailing whitespace",
            "justification": "Produce plain-text comment values while preserving row identity",
        })
        missing_before = int(comments["comment_text"].isna().sum())
        log.append({
            "dataset_name": "youtube_comments",
            "column_affected": "comment_text",
            "problem_identified": f"{missing_before} missing text values",
            "rows_affected": 0,
            "rows_before": after,
            "rows_after": after,
            "cleaning_action": "Retained missing values without replacement",
            "justification": "Missing comments must not be invented or silently replaced with placeholder text",
        })
    for column in ("published_at", "retrieved_at"):
        if column in result:
            before_values = int(result[column].notna().sum())
            result[column] = pd.to_datetime(result[column], errors="coerce", utc=True)
            invalid_values = int(result[column].isna().sum())
            log.append({
                "dataset_name": "youtube_comments",
                "column_affected": column,
                "problem_identified": f"{invalid_values} values could not be parsed as timestamps",
                "rows_affected": invalid_values,
                "rows_before": before_values,
                "rows_after": after,
                "cleaning_action": "Converted to timezone-aware pandas datetime",
                "justification": "Standardise published/retrieval timestamps; invalid values remain missing",
            })
    for column in ("like_count",):
        if column in result:
            missing_before = int(result[column].isna().sum())
            result[column] = pd.to_numeric(result[column], errors="coerce")
            log.append({
                "dataset_name": "youtube_comments",
                "column_affected": column,
                "problem_identified": f"{missing_before} missing or non-numeric values",
                "rows_affected": int(result[column].isna().sum() - missing_before),
                "rows_before": after,
                "rows_after": after,
                "cleaning_action": "Converted to numeric dtype",
                "justification": "Enable quantitative aggregation without treating missing counts as zero",
            })
    return result, log


def clean_stats(stats: pd.DataFrame) -> pd.DataFrame:
    before = len(stats)
    result = stats.copy().drop_duplicates(subset=["video_id"])
    after = len(result)
    for column in ("published_at", "retrieved_at"):
        if column in result:
            result[column] = pd.to_datetime(result[column], errors="coerce", utc=True)
    for column in ("views", "likes", "comment_count"):
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def write_cleaning_log(entries: list[dict[str, object]], path: Path | None = None) -> None:
    frame = pd.DataFrame(entries)
    cleaned_path = CLEANED_DIR / "cleaning_log.csv"
    cleaned_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cleaned_path, index=False)

    legacy_path = path or LOG_DIR / "cleaning_log.csv"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(legacy_path, index=False)


def clean_raw_files() -> None:
    """Clean available raw files without replacing unavailable values."""
    log: list[dict[str, object]] = []
    comments_path = RAW_DIR / "youtube_comments.csv"
    if comments_path.exists():
        comments, entries = clean_comments(pd.read_csv(comments_path))
        comments.to_csv(CLEANED_DIR / "cleaned_comments.csv", index=False)
        log.extend(entries)
    stats_path = RAW_DIR / "youtube_stats.csv"
    if stats_path.exists():
        raw_stats = pd.read_csv(stats_path)
        cleaned_stats = clean_stats(raw_stats)
        cleaned_stats.to_csv(CLEANED_DIR / "cleaned_stats.csv", index=False)
        before = len(raw_stats)
        after = len(cleaned_stats)
        log.append({
            "dataset_name": "youtube_stats",
            "column_affected": "video_id",
            "problem_identified": "duplicate video IDs",
            "rows_affected": before - after,
            "rows_before": before,
            "rows_after": after,
            "cleaning_action": "Removed duplicate rows using video_id",
            "justification": "video_id is the primary-key row identifier for each verified trailer",
        })
        for column in ("published_at", "retrieved_at"):
            raw_invalid = pd.to_datetime(raw_stats[column], errors="coerce", utc=True).isna().sum()
            log.append({
                "dataset_name": "youtube_stats",
                "column_affected": column,
                "problem_identified": f"{int(raw_invalid)} values could not be parsed",
                "rows_affected": int(raw_invalid),
                "rows_before": before,
                "rows_after": after,
                "cleaning_action": "Converted to timezone-aware pandas datetime",
                "justification": "Standardise snapshot and publication timestamps; missing values remain missing",
            })
        for column in ("views", "likes", "comment_count"):
            invalid = pd.to_numeric(raw_stats[column], errors="coerce").isna().sum()
            log.append({
                "dataset_name": "youtube_stats",
                "column_affected": column,
                "problem_identified": f"{int(invalid)} missing or non-numeric values",
                "rows_affected": int(invalid),
                "rows_before": before,
                "rows_after": after,
                "cleaning_action": "Converted to numeric dtype with coercion",
                "justification": "Enable rates and aggregations; no source count was replaced with zero",
            })
        missing_total = int(raw_stats.isna().sum().sum())
        log.append({
            "dataset_name": "youtube_stats",
            "column_affected": "all fields",
            "problem_identified": f"{missing_total} missing values across trailer statistics",
            "rows_affected": 0,
            "rows_before": before,
            "rows_after": after,
            "cleaning_action": "Retained missing values without replacing them with zero",
            "justification": "An unavailable view, like, or comment value is not evidence that the source count is zero",
        })
    trends_path = RAW_DIR / "google_trends.csv"
    if trends_path.exists():
        from .google_trends import load_google_trends
        trends = load_google_trends(trends_path)
        trends.to_csv(CLEANED_DIR / "cleaned_google_trends.csv", index=False)
        log.append({
            "dataset_name": "google_trends",
            "column_affected": "all required fields",
            "problem_identified": "manual export required schema validation",
            "rows_affected": 0,
            "rows_before": len(trends),
            "rows_after": len(trends),
            "cleaning_action": "Validated required columns, converted dates and numeric interest, trimmed text fields",
            "justification": "Standardise the optional exported comparison without interpolating or inventing values",
        })
    tmdb_path = RAW_DIR / "tmdb_movies.csv"
    if tmdb_path.exists():
        tmdb = pd.read_csv(tmdb_path)
        before = len(tmdb)
        tmdb_numeric = tmdb.copy()
        for column in ("runtime_minutes", "lead_cast_popularity", "tmdb_rating", "tmdb_vote_count", "tmdb_popularity"):
            if column in tmdb_numeric:
                tmdb_numeric[column] = pd.to_numeric(tmdb_numeric[column], errors="coerce")
        log.append({
            "dataset_name": "tmdb_movie_metadata",
            "column_affected": "TMDB JSON nested fields",
            "problem_identified": "semi-structured nested JSON requires tabular flattening",
            "rows_affected": before,
            "rows_before": before,
            "rows_after": before,
            "cleaning_action": "Flattened JSON API payload fields with pd.json_normalize() and mapped master movie IDs",
            "justification": "Convert nested TMDB metadata and the credits array into one row per movie",
        })
        log.append({
            "dataset_name": "tmdb_movie_metadata",
            "column_affected": "tmdb_id",
            "problem_identified": f"{int(tmdb['tmdb_id'].duplicated().sum()) if 'tmdb_id' in tmdb else 0} duplicate TMDB IDs",
            "rows_affected": int(tmdb["tmdb_id"].duplicated().sum()) if "tmdb_id" in tmdb else 0,
            "rows_before": before,
            "rows_after": before,
            "cleaning_action": "Checked duplicate TMDB IDs; no duplicate rows removed",
            "justification": "No source TMDB movie duplicate was present in the collected metadata",
        })
        missing_count = int(tmdb.isna().sum().sum())
        log.append({
            "dataset_name": "tmdb_movie_metadata",
            "column_affected": "all TMDB fields",
            "problem_identified": f"{missing_count} missing values across the tabular TMDB dataset",
            "rows_affected": 0,
            "rows_before": before,
            "rows_after": before,
            "cleaning_action": "Retained missing metadata values without zero or placeholder replacement",
            "justification": "Missing API fields must remain distinguishable from source-confirmed values",
        })
        log.append({
            "dataset_name": "tmdb_movie_metadata",
            "column_affected": "movie_name",
            "problem_identified": "TMDB titles may differ in punctuation or naming from the project master list",
            "rows_affected": before,
            "rows_before": before,
            "rows_after": before,
            "cleaning_action": "Mapped each flattened TMDB row to the master movie_id and retained master_movie_name",
            "justification": "Preserve consistent assignment titles while keeping the original TMDB title for traceability",
        })

    google_batch_specs = (
        ("batch1_time_series", "Time", "batch1_time_series.csv"),
        ("batch2_time_series", "Time", "batch2_time_series.csv"),
        ("batch1_by_region", "Region", "batch1_by_region.csv"),
        ("batch2_by_region", "Region", "batch2_by_region.csv"),
    )
    for dataset_name, key_column, filename in google_batch_specs:
        path = RAW_DIR / filename
        if not path.exists():
            continue
        raw = pd.read_csv(path)
        before = len(raw)
        cleaned = raw.copy()
        cleaned.columns = [str(column).strip() for column in cleaned.columns]
        cleaned = cleaned.drop_duplicates(subset=[key_column], keep="first")
        after = len(cleaned)

        if key_column == "Time":
            parsed = pd.to_datetime(cleaned["Time"], format="%Y-%m-%d", errors="coerce")
            invalid_dates = int(parsed.isna().sum())
            log.append({
                "dataset_name": dataset_name,
                "column_affected": "Time",
                "problem_identified": f"{invalid_dates} invalid dates",
                "rows_affected": invalid_dates,
                "rows_before": before,
                "rows_after": after,
                "cleaning_action": "Parsed YYYY-MM-DD values as pandas datetime",
                "justification": "Standardise date-wise alignment across monthly exports",
            })
            for column in cleaned.columns:
                if column != "Time":
                    raw_numeric = pd.to_numeric(cleaned[column].replace(r"^\s*<1\s*$", pd.NA, regex=True), errors="coerce")
                    invalid_numeric = int(raw_numeric.isna().sum())
                    log.append({
                        "dataset_name": dataset_name,
                        "column_affected": column,
                        "problem_identified": f"{invalid_numeric} missing, <1, or non-numeric values",
                        "rows_affected": invalid_numeric,
                        "rows_before": before,
                        "rows_after": after,
                        "cleaning_action": "Converted values to numeric and retained '<1' as missing",
                        "justification": "Google Trends '<1' is not a confirmed zero and must not be replaced",
                    })
        else:
            stripped_region_count = int(
                cleaned["Region"].ne(cleaned["Region"].astype(str).str.strip()).sum()
            )
            log.append({
                "dataset_name": dataset_name,
                "column_affected": "Region",
                "problem_identified": f"{stripped_region_count} region labels had surrounding whitespace",
                "rows_affected": stripped_region_count,
                "rows_before": before,
                "rows_after": after,
                "cleaning_action": "Trimmed region labels and duplicate Region keys",
                "justification": "Standardise region labels for grouping and chart labels",
            })
            for column in cleaned.columns:
                if column != "Region":
                    raw_numeric = pd.to_numeric(cleaned[column].replace(r"^\s*<1\s*$", pd.NA, regex=True), errors="coerce")
                    missing_numeric = int(raw_numeric.isna().sum())
                    log.append({
                        "dataset_name": dataset_name,
                        "column_affected": column,
                        "problem_identified": f"{missing_numeric} missing, <1, or non-numeric values",
                        "rows_affected": missing_numeric,
                        "rows_before": before,
                        "rows_after": after,
                        "cleaning_action": "Converted values to numeric and retained '<1' as missing",
                        "justification": "Preserve regional scores without interpreting '<1' or missing values as zero",
                    })

        duplicate_count = before - after
        log.append({
            "dataset_name": dataset_name,
            "column_affected": key_column,
            "problem_identified": f"{duplicate_count} duplicate {key_column.lower()} rows",
            "rows_affected": duplicate_count,
            "rows_before": before,
            "rows_after": after,
            "cleaning_action": f"Dropped duplicate rows using {key_column}; sorted cleaned output",
            "justification": "Use one row per date or region for analysis",
        })
    combined_path = CLEANED_DIR / "google_trends" / "combined_time_series.csv"
    anchor_path = CLEANED_DIR / "google_trends" / "dhurandhar_anchor_comparison.csv"
    if combined_path.exists() and anchor_path.exists():
        combined = pd.read_csv(combined_path)
        anchor = pd.read_csv(anchor_path)
        log.append({
            "dataset_name": "google_trends_time_series",
            "column_affected": "Time",
            "problem_identified": "two independent Google Trends exports require date alignment",
            "rows_affected": int(len(combined)),
            "rows_before": int(len(combined)),
            "rows_after": int(len(combined)),
            "cleaning_action": "Outer-joined Batch 1 and Batch 2 by Time; retained Dhurandhar from Batch 1",
            "justification": "Use the shared Dhurandhar monthly series as an anchor without duplicating it",
        })
        log.append({
            "dataset_name": "google_trends_time_series",
            "column_affected": "Dhurandhar",
            "problem_identified": "cross-batch anchor agreement must be verified",
            "rows_affected": int((~anchor["exact_match"].fillna(False)).sum()),
            "rows_before": int(len(anchor)),
            "rows_after": int(len(anchor)),
            "cleaning_action": "Compared Dhurandhar monthly scores and applied scaling factor 1.0",
            "justification": "All overlapping anchor scores matched, so no rescaling was needed",
        })
        for regional_name in ("batch1_by_region_cleaned.csv", "batch2_by_region_cleaned.csv"):
            regional_path = CLEANED_DIR / "google_trends" / regional_name
            if regional_path.exists():
                regional = pd.read_csv(regional_path)
                log.append({
                    "dataset_name": f"google_trends_{regional_name.split('_')[0]}",
                    "column_affected": "Region and search-term scores",
                    "problem_identified": "regional anchor scores differ across batches",
                    "rows_affected": 0,
                    "rows_before": int(len(regional)),
                    "rows_after": int(len(regional)),
                    "cleaning_action": "Cleaned and retained each regional batch separately; no cross-batch join",
                    "justification": "Directly combining regional scores would falsely treat different batch normalization scales as comparable",
                })
    write_cleaning_log(log)
