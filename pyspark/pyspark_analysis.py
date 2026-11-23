#!/usr/bin/env python3
"""
IMDb 50K Movie Reviews - PySpark analysis (Release Day Radar project).

Pipeline
--------
1. Load the Kaggle CSV ("IMDB Dataset.csv": columns `review`, `sentiment`).
2. Inspect columns and data types.
3. Clean the review text (drop null/empty rows, lowercase, strip HTML).
4. Remove duplicate reviews and count how many were removed.
5. Compute review length (characters) and word count per review.
6. Group by sentiment and aggregate (counts, duplicates removed, average length,
   average words, ...).
7. Save the aggregated results to the output folder.
8. Report how many records were processed (the dataset has 50,000).

Usage
-----
    python src/pyspark_analysis.py
    python src/pyspark_analysis.py --input "/path/to/IMDB Dataset.csv" --output output

Dataset: https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews
"""

import argparse
import glob
import json
import shutil
import sys
import time
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

# By default the CSV is read from, and results are written to, the folder that
# contains this script. Override with --input / --output.
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "IMDB Dataset.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "output"

REQUIRED_COLUMNS = ["review", "sentiment"]
EXPECTED_RECORDS = 50_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PySpark analysis of the IMDb 50K reviews dataset.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"Path to 'IMDB Dataset.csv' (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"Output folder for aggregated results (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--min-records", type=int, default=EXPECTED_RECORDS,
                        help="Fail (exit code 1) if fewer records than this are read.")
    return parser.parse_args()


def build_spark() -> SparkSession:
    """Local Spark session. Few shuffle partitions: the data is small (~65 MB)."""
    spark = (
        SparkSession.builder
        .appName("IMDb50K-Analysis")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def load_reviews(spark: SparkSession, path: Path) -> DataFrame:
    """
    Load the CSV.

    Reviews contain commas, double quotes and line breaks, so:
      - multiLine=True lets one record span several physical lines
      - quote/escape = '"' follow the standard CSV rule that a quote inside a quoted
        field is written as two quotes ("")
    inferSchema is off on purpose: both columns are text, so no extra pass over the
    data is needed and nothing is mis-typed.
    """
    return (
        spark.read
        .option("header", True)
        .option("multiLine", True)
        .option("quote", '"')
        .option("escape", '"')
        .csv(str(path))
    )


def inspect(df: DataFrame) -> None:
    """Print columns and data types, and verify the columns we depend on exist."""
    print("\n=== Schema ===")
    df.printSchema()
    print("Columns and data types:", df.dtypes)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: expected columns {REQUIRED_COLUMNS}, but {missing} not found "
                 f"in {df.columns}. Is this the right file?")


def clean_reviews(df: DataFrame) -> DataFrame:
    """
    Cleaning steps (each step is a separate column transformation):
      1. normalise `sentiment` (trim + lowercase) so 'Positive ' == 'positive'
      2. drop rows with null/blank review or null sentiment
      3. lowercase the review
      4. replace HTML tags (e.g. <br />) with a space
      5. replace HTML entities (e.g. &amp;, &#39;) with a space
      6. collapse repeated whitespace and trim
      7. drop reviews that are empty after cleaning (e.g. a review that was only tags)
    """
    return (
        df.select("review", F.lower(F.trim(F.col("sentiment"))).alias("sentiment"))      # 1
        .filter(F.col("review").isNotNull() & (F.trim(F.col("review")) != ""))           # 2
        .filter(F.col("sentiment").isNotNull() & (F.col("sentiment") != ""))            # 2
        .withColumn("clean_review", F.lower(F.col("review")))                            # 3
        .withColumn("clean_review", F.regexp_replace("clean_review", r"<[^>]+>", " "))   # 4
        .withColumn("clean_review", F.regexp_replace("clean_review", r"&(#\d+|[a-z]+);", " "))  # 5
        .withColumn("clean_review", F.trim(F.regexp_replace("clean_review", r"\s+", " ")))      # 6
        .filter(F.length("clean_review") > 0)                                            # 7
    )


def remove_duplicates(df: DataFrame) -> DataFrame:
    """
    Keep one row per distinct (cleaned review, sentiment). Matching on the cleaned
    text means reviews that differ only in capitalisation or HTML tags count as
    duplicates. Including sentiment means a review that appears twice with
    different labels is not silently collapsed into one arbitrary label.
    """
    return df.dropDuplicates(["clean_review", "sentiment"])


def add_text_metrics(df: DataFrame) -> DataFrame:
    """
    review_length: number of characters in the cleaned review.
    word_count:    number of whitespace-separated tokens in the cleaned review.
                   Whitespace is already collapsed to single spaces, so splitting on
                   a single space is exact.
    """
    return (
        df.withColumn("review_length", F.length("clean_review"))
          .withColumn("word_count", F.size(F.split("clean_review", " ")))
    )


def aggregate_by_sentiment(df: DataFrame) -> DataFrame:
    """
    One row per sentiment plus an 'ALL' total row (rollup adds the grand total as a
    row whose sentiment is NULL, which we rename).
    """
    return (
        df.rollup("sentiment")
        .agg(
            F.count("*").alias("review_count"),
            F.round(F.avg("review_length"), 2).alias("avg_review_length"),
            F.round(F.avg("word_count"), 2).alias("avg_word_count"),
            F.min("review_length").alias("min_review_length"),
            F.max("review_length").alias("max_review_length"),
            F.min("word_count").alias("min_word_count"),
            F.max("word_count").alias("max_word_count"),
        )
        .withColumn("sentiment", F.coalesce(F.col("sentiment"), F.lit("ALL")))
        .orderBy(F.when(F.col("sentiment") == "ALL", 1).otherwise(0), F.col("sentiment"))
    )


def add_duplicate_counts(summary: DataFrame, before_dedup: DataFrame) -> DataFrame:
    """
    Add `reviews_before_dedup` and `duplicates_removed` columns to the summary table,
    for each sentiment and for the 'ALL' total row.
    """
    before = (
        before_dedup.rollup("sentiment").count()
        .withColumn("sentiment", F.coalesce(F.col("sentiment"), F.lit("ALL")))
        .withColumnRenamed("count", "reviews_before_dedup")
    )
    other_cols = [c for c in summary.columns if c not in ("sentiment", "review_count")]
    return (
        summary.join(before, on="sentiment", how="left")
        .withColumn("duplicates_removed", F.col("reviews_before_dedup") - F.col("review_count"))
        .select("sentiment", "reviews_before_dedup", "duplicates_removed", "review_count", *other_cols)
        .orderBy(F.when(F.col("sentiment") == "ALL", 1).otherwise(0), F.col("sentiment"))
    )


def save_single_csv(df: DataFrame, target: Path) -> None:
    """
    Spark always writes a folder of part files. For a small aggregate table we want a
    single, normally named CSV, so write one partition to a temp folder and move the
    part file to `target`.
    """
    tmp_dir = target.parent / f"_tmp_{target.stem}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    df.coalesce(1).write.mode("overwrite").option("header", True).csv(str(tmp_dir))

    part_files = glob.glob(str(tmp_dir / "part-*.csv"))
    if not part_files:
        sys.exit(f"ERROR: Spark wrote no part file to {tmp_dir}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(part_files[0], target)
    shutil.rmtree(tmp_dir)


def main() -> None:
    args = parse_args()
    started = time.time()

    if not args.input.exists():
        sys.exit(
            f"ERROR: dataset not found at: {args.input}\n"
            "Download 'IMDB Dataset.csv' from\n"
            "  https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews\n"
            "and either place it in the project's data/ folder or pass --input <path>."
        )

    spark = build_spark()

    # 1. Load + 2. inspect
    raw = load_reviews(spark, args.input)
    inspect(raw)

    # 3. Clean (nulls, blanks, HTML, lowercase). cache() because the data is reused
    #    by several actions below.
    before_dedup = clean_reviews(raw).cache()

    # 4. Remove duplicates, then add length / word count
    cleaned = add_text_metrics(remove_duplicates(before_dedup)).cache()

    # Record counts (first action: triggers the actual read + cleaning)
    raw_count = raw.count()
    before_dedup_count = before_dedup.count()
    cleaned_count = cleaned.count()
    duplicates_removed = before_dedup_count - cleaned_count
    print("\n=== Records ===")
    print(f"Records read from CSV           : {raw_count:,}")
    print(f"Dropped (null / empty reviews)  : {raw_count - before_dedup_count:,}")
    print(f"Duplicate reviews removed       : {duplicates_removed:,}")
    print(f"Records after cleaning + dedup  : {cleaned_count:,}")

    # Show the effect of cleaning on a few reviews
    print("\n=== Cleaning examples (raw vs cleaned) ===")
    cleaned.select(F.substring("review", 1, 90).alias("raw_review_start"),
                   F.substring("clean_review", 1, 90).alias("clean_review_start"),
                   "review_length", "word_count").show(3, truncate=False)

    # 5. Group by sentiment
    summary = add_duplicate_counts(aggregate_by_sentiment(cleaned), before_dedup)
    print("=== Aggregated results by sentiment ===")
    summary.show(truncate=False)

    # 6. Save aggregated results
    args.output.mkdir(parents=True, exist_ok=True)
    summary_csv = args.output / "sentiment_summary.csv"
    save_single_csv(summary, summary_csv)

    elapsed = round(time.time() - started, 1)
    run_info = {
        "input_file": str(args.input),
        "records_read": raw_count,
        "records_dropped_null_or_empty": raw_count - before_dedup_count,
        "duplicates_removed": duplicates_removed,
        "records_after_cleaning_and_dedup": cleaned_count,
        "min_records_required": args.min_records,
        "processed_at_least_min_records": raw_count >= args.min_records,
        "runtime_seconds": elapsed,
        "spark_version": spark.version,
    }
    run_json = args.output / "run_summary.json"
    run_json.write_text(json.dumps(run_info, indent=2))

    print(f"Saved: {summary_csv}")
    print(f"Saved: {run_json}")

    # 7. Demonstrate 50,000-record processing
    ok = raw_count >= args.min_records
    print(f"\n{'PASS' if ok else 'FAIL'}: processed {raw_count:,} records "
          f"(required >= {args.min_records:,}) in {elapsed}s")

    cleaned.unpersist()
    before_dedup.unpersist()
    spark.stop()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()