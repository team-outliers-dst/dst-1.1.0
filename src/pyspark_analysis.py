"""Separate PySpark processing for the general IMDb 50K corpus."""

from __future__ import annotations

import re
from pathlib import Path


def run_imdb_analysis(input_path: str | Path, output_path: str | Path) -> None:
    try:
        from pyspark.sql import SparkSession, functions as F
    except ImportError as exc:
        raise RuntimeError("Install pyspark to run the IMDb corpus analysis.") from exc
    spark = SparkSession.builder.appName("ReleaseDayRadarIMDb").getOrCreate()
    try:
        frame = spark.read.option("header", True).option("inferSchema", True).csv(str(input_path))
        clean_text = F.regexp_replace(F.lower(F.col("review")), "<[^>]*>", "")
        result = frame.withColumn("clean_review", clean_text)
        result = result.withColumn("review_length", F.length("clean_review"))
        result = result.withColumn("word_count", F.size(F.split(F.trim("clean_review"), r"\s+")))
        summary = result.groupBy("sentiment").agg(
            F.count("*").alias("review_count"),
            F.avg("review_length").alias("average_review_length"),
            F.avg("word_count").alias("average_word_count"),
        )
        summary.coalesce(1).write.mode("overwrite").option("header", True).csv(str(output_path))
        total = result.count()
        if total < 50000:
            raise ValueError(f"Expected at least 50,000 IMDb records, processed {total}.")
    finally:
        spark.stop()
