"""
Excel vs Pandas — Side-by-side cleaning comparison
Case Study A: Release Day Radar
Module 1 requirement: Spreadsheets and Dataframes

Cleaning step demonstrated
--------------------------
Problem : published_at is stored as an ISO-8601 string ("2025-11-18T06:50:49Z")
          in youtube_stats.csv.  Excel reads it as plain text; pandas reads it
          as dtype=object.  Both must convert it to a proper date so we can
          compute trailer-launch-to-release-day lag.

This script reproduces the pandas half of the comparison programmatically and
writes an annotated copy of the data to data/cleaned/excel_vs_pandas_demo.csv.

The Excel half is documented below in comments and in the report note
(docs/excel_vs_pandas_note.md).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]
RAW_CSV = BASE / "data" / "raw" / "youtube_stats.csv"
OUT_CSV = BASE / "data" / "cleaned" / "excel_vs_pandas_demo.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Step 0 — load exactly as pandas sees the raw file (mirrors opening in Excel)
# ---------------------------------------------------------------------------
raw = pd.read_csv(RAW_CSV)
print("=== RAW (before cleaning) ===")
print(raw[["video_id", "movie_name", "published_at", "views"]].to_string(index=False))
print(f"\ndtype of published_at : {raw['published_at'].dtype}")
print(f"dtype of views        : {raw['views'].dtype}")

# ---------------------------------------------------------------------------
# Step 1 — convert published_at from string → timezone-aware datetime
#           (pandas equivalent of Excel's "Text to Columns" + Format Cells)
# ---------------------------------------------------------------------------
cleaned = raw.copy()
cleaned["published_at"] = pd.to_datetime(cleaned["published_at"], errors="coerce", utc=True)

print("\n=== AFTER pandas pd.to_datetime() ===")
print(cleaned[["video_id", "movie_name", "published_at"]].to_string(index=False))
print(f"\ndtype of published_at : {cleaned['published_at'].dtype}")

# ---------------------------------------------------------------------------
# Step 2 — derive trailer_launch_date (date only, no time zone noise)
# ---------------------------------------------------------------------------
cleaned["trailer_launch_date"] = cleaned["published_at"].dt.date

# Load release dates from movie master for lag calculation
movie_master = pd.read_csv(BASE / "data" / "raw" / "movie_master.csv")
movie_master["release_date"] = pd.to_datetime(movie_master["release_date"])

merged = cleaned.merge(
    movie_master[["movie_id", "release_date"]],
    on="movie_id",
    how="left",
)

cleaned["release_date"] = merged["release_date"]
cleaned["days_before_release"] = (
    cleaned["release_date"] - cleaned["published_at"].dt.tz_localize(None)
).dt.days

print("\n=== WITH lag column (days trailer launched before release) ===")
print(
    cleaned[["movie_name", "trailer_launch_date", "release_date", "days_before_release"]]
    .to_string(index=False)
)

# ---------------------------------------------------------------------------
# Step 3 — save annotated CSV
# ---------------------------------------------------------------------------
cleaned.to_csv(OUT_CSV, index=False)
print(f"\nSaved cleaned demo to: {OUT_CSV}")

# ---------------------------------------------------------------------------
# Step 4 — print a compact comparison table for copy-paste into the report
# ---------------------------------------------------------------------------
print("\n" + "=" * 68)
print("SIDE-BY-SIDE COMPARISON TABLE")
print("=" * 68)
comparison = {
    "Aspect": [
        "Tool",
        "File opened",
        "Raw dtype of published_at",
        "Cleaning action",
        "Formula / code",
        "New column name",
        "Result dtype",
        "Null-safe?",
        "Reproducible?",
        "Effort",
    ],
    "Excel": [
        "Microsoft Excel 365",
        "youtube_stats.csv",
        'Text (General, shown as "2025-11-18T06:50:49Z")',
        "Text to Columns (delimiter: T) → keep date part → Format Cells → Date",
        '=DATEVALUE(LEFT(B2,10))  then Format → Date',
        "published_date (manual column D)",
        "Serial number (Excel date)",
        "No — must wrap in IFERROR() manually",
        "No — manual clicks, not recorded",
        "~5 mins, 3 dialog boxes",
    ],
    "Pandas": [
        "Python 3 + pandas",
        "youtube_stats.csv",
        "object (string)",
        "pd.to_datetime() with errors='coerce' and utc=True",
        "df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)",
        "published_at (in-place, dtype changed)",
        "datetime64[ns, UTC]",
        "Yes — invalid strings become NaT automatically",
        "Yes — script reruns identically from raw file",
        "1 line, ~1 second",
    ],
}

cmp_df = pd.DataFrame(comparison)
print(cmp_df.to_string(index=False))
