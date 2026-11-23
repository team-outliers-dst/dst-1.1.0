"""Clean and align the manually downloaded Google Trends exports."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
CLEANED_DIR = Path(__file__).resolve().parents[1] / "data" / "cleaned" / "google_trends"
VISUALIZATIONS_DIR = Path(__file__).resolve().parents[1] / "visualizations"


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load one original export and strip column names and string whitespace."""
    data = pd.read_csv(path)
    data.columns = [str(column).strip() for column in data.columns]
    for column in data.select_dtypes(include=["object"]).columns:
        data[column] = data[column].apply(
            lambda value: value.strip() if isinstance(value, str) else value
        )
    return data


def clean_time_series(path: str | Path) -> pd.DataFrame:
    """Convert wide monthly scores to a clean date-indexed wide table."""
    data = load_csv(path)
    if "Time" not in data.columns:
        raise ValueError(f"{path} does not contain the Google Trends 'Time' column.")

    data["Time"] = pd.to_datetime(data["Time"], format="%Y-%m-%d", errors="coerce")
    data = data.drop_duplicates(subset=["Time"], keep="first")
    data = data.sort_values("Time").reset_index(drop=True)
    if data["Time"].isna().any():
        raise ValueError(f"{path} contains an invalid date that could not be parsed.")

    for column in data.columns:
        if column != "Time":
            # "<1" is not a zero. Retain it as missing rather than fabricating 0 or 1.
            data[column] = data[column].replace(r"^\s*<1\s*$", pd.NA, regex=True)
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def clean_region(path: str | Path) -> pd.DataFrame:
    """Clean one regional export without combining it with another batch."""
    data = load_csv(path)
    if "Region" not in data.columns:
        raise ValueError(f"{path} does not contain the Google Trends 'Region' column.")

    data = data.drop_duplicates(subset=["Region"], keep="first")
    for column in data.columns:
        if column != "Region":
            data[column] = data[column].replace(r"^\s*<1\s*$", pd.NA, regex=True)
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data.sort_values("Region").reset_index(drop=True)


def verify_anchor(batch1: pd.DataFrame, batch2: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Compare overlapping Dhurandhar scores and calculate a defensible scale factor."""
    comparison = batch1[["Time", "Dhurandhar"]].merge(
        batch2[["Time", "Dhurandhar"]],
        on="Time",
        how="inner",
        suffixes=("_batch1", "_batch2"),
    )
    comparison["exact_match"] = (
        comparison["Dhurandhar_batch1"].eq(comparison["Dhurandhar_batch2"])
    )
    comparison["difference"] = (
        comparison["Dhurandhar_batch1"] - comparison["Dhurandhar_batch2"]
    )

    valid = comparison[
        comparison["Dhurandhar_batch1"].notna()
        & comparison["Dhurandhar_batch2"].notna()
        & comparison["Dhurandhar_batch2"].ne(0)
    ]
    if valid.empty:
        scale_factor = 1.0
    else:
        ratios = (
            valid["Dhurandhar_batch1"] / valid["Dhurandhar_batch2"]
        ).replace([float("inf"), float("-inf")], pd.NA).dropna()
        scale_factor = float(ratios.median()) if not ratios.empty else 1.0

    # If the anchor is already exact, no scaling is required or applied.
    if comparison["exact_match"].fillna(False).all():
        scale_factor = 1.0
    return comparison, scale_factor


def combine_time_series(
    batch1: pd.DataFrame,
    batch2: pd.DataFrame,
    scale_factor: float,
) -> pd.DataFrame:
    """Combine batches with batch1 as the reference scale."""
    batch2_adjusted = batch2.copy()
    for column in batch2_adjusted.columns:
        if column not in {"Time", "Dhurandhar"}:
            batch2_adjusted[column] = batch2_adjusted[column] * scale_factor

    combined = batch1.merge(
        batch2_adjusted.drop(columns=["Dhurandhar"]),
        on="Time",
        how="outer",
        validate="one_to_one",
        suffixes=("", "_batch2"),
    )
    return combined.sort_values("Time").reset_index(drop=True)


def to_long(data: pd.DataFrame) -> pd.DataFrame:
    """Convert date-wise wide scores to a long, analysis-friendly dataset."""
    return data.melt(
        id_vars=["Time"],
        var_name="movie_name",
        value_name="search_interest_0_100",
    ).dropna(subset=["search_interest_0_100"])


def identify_peaks(combined: pd.DataFrame) -> pd.DataFrame:
    """Identify the month with the maximum available score for each movie."""
    long = to_long(combined)
    valid = long.dropna(subset=["search_interest_0_100"])
    peaks = (
        valid.sort_values(["movie_name", "search_interest_0_100", "Time"],
                          ascending=[True, False, True])
        .groupby("movie_name", as_index=False)
        .first()
        .rename(columns={
            "Time": "peak_month",
            "search_interest_0_100": "peak_search_interest",
        })
    )
    return peaks


def plot_time_series(combined: pd.DataFrame) -> Path:
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    VISUALIZATIONS_DIR.mkdir(parents=True, exist_ok=True)

    output = VISUALIZATIONS_DIR / "google_trends_monthly_search_interest.png"
    figure, ax = plt.subplots(figsize=(13, 7))
    for movie in combined.columns:
        if movie != "Time":
            ax.plot(combined["Time"], combined[movie], marker="o", linewidth=1.5, label=movie)
    ax.set_title("Monthly Google Trends Search Interest")
    ax.set_xlabel("Month")
    ax.set_ylabel("Google Trends interest (0-100; relative)")
    ax.grid(True, alpha=0.3)
    ax.legend(ncol=2, fontsize=9)
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)
    return output


def plot_regional(batch: pd.DataFrame, batch_name: str) -> Path:
    """Plot regional top-Dhurandhar regions separately for each batch."""
    VISUALIZATIONS_DIR.mkdir(parents=True, exist_ok=True)
    if "Dhurandhar" not in batch.columns:
        raise ValueError(f"{batch_name} regional data has no Dhurandhar anchor.")

    top_regions = batch.sort_values("Dhurandhar", ascending=False).head(15)
    terms = [column for column in top_regions.columns if column not in {"Region"}]
    top_regions.set_index("Region")[terms].plot(
        kind="bar",
        figsize=(14, 7),
    )
    plt.title(f"Regional Google Trends Comparison - {batch_name}")
    plt.xlabel("Region")
    plt.ylabel("Google Trends interest (0-100; relative)")
    plt.xticks(rotation=75, ha="right")
    plt.legend(title="Search term")
    plt.tight_layout()
    output = VISUALIZATIONS_DIR / f"google_trends_{batch_name.lower()}_region.png"
    plt.savefig(output, dpi=160)
    plt.close()
    return output


def write_methodology(
    output_path: Path,
    anchor_comparison: pd.DataFrame,
    scale_factor: float,
) -> None:
    exact = bool(anchor_comparison["exact_match"].fillna(False).all())
    methodology = f"""# Google Trends Scaling and Alignment

Google Trends scores are relative search-interest indices, not absolute search
volumes. A maximum observed search term is usually assigned 100 within one export.

- Batch 1 terms: Dhurandhar, Chhaava, Coolie, Good Bad Ugly.
- Batch 2 terms: Su From So, Ekka, L2: Empuraan, Lokah Chapter 1: Chandra,
  Dhurandhar.
- The overlapping Dhurandhar series is the only cross-batch anchor.
- Both monthly exports were outer-aligned by the `Time` date and duplicate dates
  were removed. Missing values were preserved and never converted to zero.
- Monthly Dhurandhar matches exactly across the overlapping dates: `{exact}`.
- Median overlap-based scale factor: `{scale_factor:.12g}`.
- Batch 1 remains on its original scale. Batch 2 values are multiplied by the
  median anchor ratio only if the original anchor series differs. Non-anchor
  Batch 2 values are also treated as estimates on the Batch 1 scale.
- Dhurandhar itself is taken from Batch 1 in the combined dataset to avoid
  duplicating or modifying its verified overlap values.
- Regional scores were not cross-batch aligned or combined. Dhurandhar's
  regional anchors differ between batches, so Batch 1 and Batch 2 regional
  data are kept and analysed separately.
- Combined figures should be interpreted as normalized comparative indices,
  not actual search counts or causal measures of audience demand.
"""
    output_path.write_text(methodology, encoding="utf-8")


def run(raw_dir: str | Path = RAW_DIR) -> dict[str, pd.DataFrame | Path]:
    raw_dir = Path(raw_dir)
    batch1_path = raw_dir / "batch1_time_series.csv"
    batch2_path = raw_dir / "batch2_time_series.csv"
    batch1_region_path = raw_dir / "batch1_by_region.csv"
    batch2_region_path = raw_dir / "batch2_by_region.csv"

    batch1 = clean_time_series(batch1_path)
    batch2 = clean_time_series(batch2_path)
    batch1_region = clean_region(batch1_region_path)
    batch2_region = clean_region(batch2_region_path)

    anchor_comparison, scale_factor = verify_anchor(batch1, batch2)
    combined = combine_time_series(batch1, batch2, scale_factor)
    peaks = identify_peaks(combined)

    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    batch1.to_csv(CLEANED_DIR / "batch1_time_series_cleaned.csv", index=False)
    batch2.to_csv(CLEANED_DIR / "batch2_time_series_cleaned.csv", index=False)
    combined.to_csv(CLEANED_DIR / "combined_time_series.csv", index=False)
    to_long(combined).to_csv(CLEANED_DIR / "combined_time_series_long.csv", index=False)
    batch1_region.to_csv(CLEANED_DIR / "batch1_by_region_cleaned.csv", index=False)
    batch2_region.to_csv(CLEANED_DIR / "batch2_by_region_cleaned.csv", index=False)
    anchor_comparison.to_csv(CLEANED_DIR / "dhurandhar_anchor_comparison.csv", index=False)
    peaks.to_csv(CLEANED_DIR / "monthly_search_interest_peaks.csv", index=False)

    monthly_chart = plot_time_series(combined)
    batch1_chart = plot_regional(batch1_region, "Batch1")
    batch2_chart = plot_regional(batch2_region, "Batch2")
    write_methodology(
        CLEANED_DIR / "google_trends_methodology.md",
        anchor_comparison,
        scale_factor,
    )
    return {
        "batch1": batch1,
        "batch2": batch2,
        "batch1_region": batch1_region,
        "batch2_region": batch2_region,
        "combined": combined,
        "peaks": peaks,
        "anchor_comparison": anchor_comparison,
        "monthly_chart": monthly_chart,
        "batch1_chart": batch1_chart,
        "batch2_chart": batch2_chart,
    }


if __name__ == "__main__":
    outputs = run()
    print(f"Processed Dhurandhar anchor comparisons: {len(outputs['anchor_comparison'])}")
    print(f"Combined monthly rows: {len(outputs['combined'])}")
    print(f"Monthly peaks: {len(outputs['peaks'])}")
