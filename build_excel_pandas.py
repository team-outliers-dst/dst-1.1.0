"""
Build the Excel vs Pandas deliverable set for Case Study A — Release Day Radar.

Mirrors the structure from the previous case study:
  excel/
      Trailer_Engagement_Analysis.xlsx    ← raw data + typed sheet + pivot sheet
      excel_pivot_values.xlsx             ← pivot values only (for comparison CSV)
  pandas/
      trailer_pandas_analysis.py          ← the runnable analysis script
      engagement_by_film.csv
      engagement_by_language.csv
      trailer_lag_pivot.csv
      excel_pandas_difference.csv
      views_likes_heatmap.png

Run from the project root:
    python build_excel_pandas.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    PatternFill,
    Side,
)
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
RAW_CSV    = BASE / "data" / "raw"  / "youtube_stats.csv"
MASTER_CSV = BASE / "data" / "raw"  / "movie_master.csv"

EXCEL_DIR  = BASE / "excel"
PANDAS_DIR = BASE / "pandas"
EXCEL_DIR.mkdir(exist_ok=True)
PANDAS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 0. Load & prepare master data
# ---------------------------------------------------------------------------
raw   = pd.read_csv(RAW_CSV)
master = pd.read_csv(MASTER_CSV, skiprows=1)   # first row blank in this file
master["release_date"] = pd.to_datetime(master["release_date"])

# Merge to get language + release_date alongside stats
df = raw.merge(master[["movie_id", "language", "release_date"]], on="movie_id", how="left")
df["published_at_raw"] = df["published_at"]                       # keep original string

# Pandas-typed version
df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
df["trailer_launch_date"] = df["published_at"].dt.date
df["days_before_release"] = (
    df["release_date"] - df["published_at"].dt.tz_localize(None)
).dt.days

# derived engagement metrics
df["like_rate"]    = (df["likes"]         / df["views"] * 100).round(2)
df["comment_rate"] = (df["comment_count"] / df["views"] * 100).round(2)

COLS_DISPLAY = [
    "movie_name", "language", "trailer_launch_date", "release_date",
    "days_before_release", "views", "likes", "comment_count",
    "like_rate", "comment_rate",
]

print("✓ Data loaded —", len(df), "trailers")

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
HEADER_FILL  = PatternFill("solid", fgColor="1F4E79")
TYPED_FILL   = PatternFill("solid", fgColor="2E75B6")
PIVOT_FILL   = PatternFill("solid", fgColor="375623")
WHITE_FONT   = Font(color="FFFFFF", bold=True)
BODY_FONT    = Font(name="Calibri", size=10)
THIN = Side(style="thin", color="BFBFBF")
THIN_BORDER  = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

LANG_COLORS = {
    "Hindi":    "FFF2CC",
    "Tamil":    "FCE4D6",
    "Kannada":  "E2EFDA",
    "Malayalam":"DDEBF7",
}

def _write_header(ws, row, headers, fill):
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=col, value=h)
        c.fill = fill
        c.font = WHITE_FONT
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        c.border = THIN_BORDER

def _auto_width(ws):
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=8)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)

# ---------------------------------------------------------------------------
# 1. Build Trailer_Engagement_Analysis.xlsx  (3 sheets)
# ---------------------------------------------------------------------------
wb = Workbook()

# ── Sheet 1: RAW DATA ───────────────────────────────────────────────────────
ws_raw = wb.active
ws_raw.title = "Raw Data"

raw_headers = [
    "video_id", "movie_name", "published_at (raw string)",
    "views", "likes", "comment_count", "duration",
]
_write_header(ws_raw, 1, raw_headers, HEADER_FILL)

for i, row_data in df.iterrows():
    r = i + 2
    vals = [
        row_data["video_id"],
        row_data["movie_name"],
        row_data["published_at_raw"],
        int(row_data["views"]),
        int(row_data["likes"]),
        int(row_data["comment_count"]),
        row_data["duration"],
    ]
    for col, v in enumerate(vals, 1):
        c = ws_raw.cell(row=r, column=col, value=v)
        c.font = BODY_FONT
        c.border = THIN_BORDER
        c.alignment = Alignment(horizontal="center")

# annotation note in row 11
ws_raw.cell(row=11, column=1,
    value="⚠  published_at column is plain text (General) — Excel cannot do date arithmetic on this directly."
).font = Font(color="C00000", italic=True)

_auto_width(ws_raw)

# ── Sheet 2: TYPED DATA (after Text-to-Columns / DATEVALUE) ─────────────────
ws_typed = wb.create_sheet("Typed & Cleaned")

typed_headers = [
    "movie_name", "language",
    "trailer_launch_date\n(=DATEVALUE(LEFT(raw,10)))",
    "release_date", "days_before_release\n(=release_date−trailer_launch)",
    "views", "likes", "comment_count",
    "like_rate (%)\n(=likes/views×100)",
    "comment_rate (%)\n(=comments/views×100)",
]
_write_header(ws_typed, 1, typed_headers, TYPED_FILL)
ws_typed.row_dimensions[1].height = 36

for i, row_data in df.iterrows():
    r = i + 2
    lang = row_data["language"]
    row_fill = PatternFill("solid", fgColor=LANG_COLORS.get(lang, "FFFFFF"))
    vals = [
        row_data["movie_name"],
        lang,
        str(row_data["trailer_launch_date"]),
        str(row_data["release_date"].date()),
        int(row_data["days_before_release"]),
        int(row_data["views"]),
        int(row_data["likes"]),
        int(row_data["comment_count"]),
        float(row_data["like_rate"]),
        float(row_data["comment_rate"]),
    ]
    for col, v in enumerate(vals, 1):
        c = ws_typed.cell(row=r, column=col, value=v)
        c.font = BODY_FONT
        c.border = THIN_BORDER
        c.fill = row_fill
        c.alignment = Alignment(horizontal="center")

# colour legend
ws_typed.cell(row=11, column=1, value="Colour legend:").font = Font(bold=True)
for col_off, (lang, hex_col) in enumerate(LANG_COLORS.items(), 2):
    c = ws_typed.cell(row=11, column=col_off, value=lang)
    c.fill = PatternFill("solid", fgColor=hex_col)
    c.font = BODY_FONT
    c.alignment = Alignment(horizontal="center")

_auto_width(ws_typed)

# ── Sheet 3: PIVOT TABLE (language × metric) ─────────────────────────────────
ws_pivot = wb.create_sheet("Pivot — Language Summary")

pivot_df = df.groupby("language").agg(
    films       =("movie_name",      "count"),
    total_views =("views",           "sum"),
    avg_views   =("views",           "mean"),
    avg_likes   =("likes",           "mean"),
    avg_comments=("comment_count",   "mean"),
    avg_like_rate   =("like_rate",   "mean"),
    avg_comment_rate=("comment_rate","mean"),
    avg_days_before =("days_before_release","mean"),
).reset_index().round(0)

pivot_headers = [
    "Language", "# Films", "Total Views",
    "Avg Views", "Avg Likes", "Avg Comments",
    "Avg Like Rate (%)", "Avg Comment Rate (%)", "Avg Days Before Release",
]
_write_header(ws_pivot, 1, pivot_headers, PIVOT_FILL)

for i, row_data in pivot_df.iterrows():
    r = i + 2
    for col, v in enumerate(row_data.values, 1):
        c = ws_pivot.cell(row=r, column=col, value=v)
        c.font = BODY_FONT
        c.border = THIN_BORDER
        c.alignment = Alignment(horizontal="center")

_auto_width(ws_pivot)

wb.save(EXCEL_DIR / "Trailer_Engagement_Analysis.xlsx")
print("✓ Saved excel/Trailer_Engagement_Analysis.xlsx")

# ── excel_pivot_values.xlsx  (pivot only, for comparison CSV) ────────────────
wb2 = Workbook()
ws2 = wb2.active
ws2.title = "Pivot Values"
_write_header(ws2, 1, pivot_headers, PIVOT_FILL)
for i, row_data in pivot_df.iterrows():
    for col, v in enumerate(row_data.values, 1):
        ws2.cell(row=i + 2, column=col, value=v)
_auto_width(ws2)
wb2.save(EXCEL_DIR / "excel_pivot_values.xlsx")
print("✓ Saved excel/excel_pivot_values.xlsx")

# ---------------------------------------------------------------------------
# 2. Pandas outputs — CSVs
# ---------------------------------------------------------------------------

# 2a. engagement_by_film.csv
film_df = df[COLS_DISPLAY].copy()
film_df.to_csv(PANDAS_DIR / "engagement_by_film.csv", index=False)
print("✓ Saved pandas/engagement_by_film.csv")

# 2b. engagement_by_language.csv
lang_df = pivot_df.copy()
lang_df.columns = [
    "language", "films", "total_views", "avg_views",
    "avg_likes", "avg_comments", "avg_like_rate_pct",
    "avg_comment_rate_pct", "avg_days_before_release",
]
lang_df.to_csv(PANDAS_DIR / "engagement_by_language.csv", index=False)
print("✓ Saved pandas/engagement_by_language.csv")

# 2c. trailer_lag_pivot.csv  (pivot: language × metric, like Excel pivot)
pivot_csv = df.pivot_table(
    index="language",
    values=["views", "likes", "comment_count", "like_rate", "comment_rate", "days_before_release"],
    aggfunc="mean",
).round(0)
pivot_csv.to_csv(PANDAS_DIR / "trailer_lag_pivot.csv")
print("✓ Saved pandas/trailer_lag_pivot.csv")

# 2d. excel_pandas_difference.csv  (key: same pivot values, side by side)
excel_pivot = pivot_df.set_index("language")[
    ["avg_views","avg_likes","avg_like_rate","avg_comment_rate","avg_days_before"]
].copy()
excel_pivot.columns = [f"excel_{c}" for c in excel_pivot.columns]

pandas_pivot = pivot_csv[["views","likes","like_rate","comment_rate","days_before_release"]].copy()
pandas_pivot.columns = [f"pandas_{c}" for c in ["avg_views","avg_likes","avg_like_rate","avg_comment_rate","avg_days_before"]]

diff_df = excel_pivot.join(pandas_pivot)
# compute deltas
for metric in ["avg_views","avg_likes","avg_like_rate","avg_comment_rate","avg_days_before"]:
    diff_df[f"delta_{metric}"] = (diff_df[f"pandas_{metric}"] - diff_df[f"excel_{metric}"]).round(4)

diff_df.to_csv(PANDAS_DIR / "excel_pandas_difference.csv")
print("✓ Saved pandas/excel_pandas_difference.csv")

# ---------------------------------------------------------------------------
# 3. Chart — views_likes_heatmap.png
# ---------------------------------------------------------------------------
# Heatmap: film (y) × metric (x), values normalised 0-1 (like a Bengaluru hour-day heatmap)
heatmap_metrics = ["views", "likes", "comment_count", "like_rate", "comment_rate", "days_before_release"]
heat_df = df.set_index("movie_name")[heatmap_metrics].copy().astype(float)

# min-max normalise each column so films of different scale are comparable
heat_norm = (heat_df - heat_df.min()) / (heat_df.max() - heat_df.min())

fig, ax = plt.subplots(figsize=(10, 5))
im = ax.imshow(heat_norm.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)

ax.set_xticks(range(len(heatmap_metrics)))
ax.set_xticklabels(
    ["Views", "Likes", "Comments", "Like Rate %", "Comment Rate %", "Days Before Release"],
    fontsize=9, rotation=30, ha="right",
)
ax.set_yticks(range(len(heat_norm)))
ax.set_yticklabels(heat_norm.index.tolist(), fontsize=9)

# annotate cells with raw values
for i in range(len(heat_norm)):
    for j, col in enumerate(heatmap_metrics):
        raw_val = heat_df.iloc[i, j]
        if col == "views":
            label = f"{raw_val/1e6:.1f}M"
        elif col in ("likes", "comment_count"):
            label = f"{raw_val/1e3:.0f}K"
        elif col in ("like_rate", "comment_rate"):
            label = f"{raw_val:.2f}%"
        else:
            label = f"{int(raw_val)}d"
        norm_val = heat_norm.values[i, j]
        txt_color = "white" if norm_val > 0.6 else "black"
        ax.text(j, i, label, ha="center", va="center", fontsize=7.5, color=txt_color)

cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cbar.set_label("Normalised score (0 = min, 1 = max)", fontsize=8)

ax.set_title(
    "Trailer Engagement by Film — Normalised (min-max) across 6 metrics\n"
    "Brighter = higher relative value within each metric",
    fontsize=10, fontweight="bold", pad=10,
)
plt.tight_layout()
fig.savefig(PANDAS_DIR / "views_likes_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ Saved pandas/views_likes_heatmap.png")

# ---------------------------------------------------------------------------
# 4. Write trailer_pandas_analysis.py  (the standalone analysis script)
# ---------------------------------------------------------------------------
ANALYSIS_SCRIPT = '''\
"""
Pandas trailer engagement analysis — Case Study A: Release Day Radar
Run from the project root:  python pandas/trailer_pandas_analysis.py
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE       = Path(__file__).resolve().parent.parent
RAW_CSV    = BASE / "data" / "raw" / "youtube_stats.csv"
MASTER_CSV = BASE / "data" / "raw" / "movie_master.csv"
OUT        = Path(__file__).resolve().parent

# ── 1. Load ──────────────────────────────────────────────────────────────────
raw    = pd.read_csv(RAW_CSV)
master = pd.read_csv(MASTER_CSV, skiprows=1)
master["release_date"] = pd.to_datetime(master["release_date"])

# ── 2. Type-cast (the cleaning step) ─────────────────────────────────────────
# published_at arrives as a plain string: "2025-11-18T06:50:49Z"
# Excel equivalent: Data → Text to Columns → Date (YMD) or =DATEVALUE(LEFT(A2,10))
raw["published_at"] = pd.to_datetime(raw["published_at"], errors="coerce", utc=True)
print("dtype after cast:", raw["published_at"].dtype)   # datetime64[ns, UTC]

# ── 3. Merge & derive columns ─────────────────────────────────────────────────
df = raw.merge(master[["movie_id", "language", "release_date"]], on="movie_id", how="left")
df["trailer_launch_date"]  = df["published_at"].dt.date
df["days_before_release"]  = (
    df["release_date"] - df["published_at"].dt.tz_localize(None)
).dt.days
df["like_rate"]    = (df["likes"]         / df["views"] * 100).round(2)
df["comment_rate"] = (df["comment_count"] / df["views"] * 100).round(2)

# ── 4. Aggregations (equivalent of Excel pivot tables) ───────────────────────
# 4a. Per-film engagement table
film_df = df[[
    "movie_name", "language", "trailer_launch_date", "release_date",
    "days_before_release", "views", "likes", "comment_count",
    "like_rate", "comment_rate",
]]
film_df.to_csv(OUT / "engagement_by_film.csv", index=False)

# 4b. Language-level pivot
lang_df = df.groupby("language").agg(
    films            =("movie_name",        "count"),
    total_views      =("views",             "sum"),
    avg_views        =("views",             "mean"),
    avg_likes        =("likes",             "mean"),
    avg_comments     =("comment_count",     "mean"),
    avg_like_rate_pct=("like_rate",         "mean"),
    avg_comment_rate_pct=("comment_rate",   "mean"),
    avg_days_before_release=("days_before_release","mean"),
).round(0).reset_index()
lang_df.to_csv(OUT / "engagement_by_language.csv", index=False)

# 4c. Full pivot (all numeric metrics × language)
pivot = df.pivot_table(
    index="language",
    values=["views","likes","comment_count","like_rate","comment_rate","days_before_release"],
    aggfunc="mean",
).round(0)
pivot.to_csv(OUT / "trailer_lag_pivot.csv")

print("\\nLanguage summary:")
print(lang_df[["language","films","avg_views","avg_like_rate_pct","avg_days_before_release"]].to_string(index=False))

# ── 5. Chart: normalised heatmap ─────────────────────────────────────────────
heatmap_cols = ["views","likes","comment_count","like_rate","comment_rate","days_before_release"]
heat = df.set_index("movie_name")[heatmap_cols].astype(float)
heat_norm = (heat - heat.min()) / (heat.max() - heat.min())

fig, ax = plt.subplots(figsize=(10, 5))
im = ax.imshow(heat_norm.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)
ax.set_xticks(range(len(heatmap_cols)))
ax.set_xticklabels(
    ["Views","Likes","Comments","Like Rate %","Comment Rate %","Days Before Release"],
    fontsize=9, rotation=30, ha="right",
)
ax.set_yticks(range(len(heat_norm)))
ax.set_yticklabels(heat_norm.index.tolist(), fontsize=9)
for i in range(len(heat_norm)):
    for j, col in enumerate(heatmap_cols):
        v = heat.iloc[i, j]
        label = (f"{v/1e6:.1f}M" if col == "views"
                 else f"{v/1e3:.0f}K" if col in ("likes","comment_count")
                 else f"{v:.2f}%" if col in ("like_rate","comment_rate")
                 else f"{int(v)}d")
        txt_color = "white" if heat_norm.values[i, j] > 0.6 else "black"
        ax.text(j, i, label, ha="center", va="center", fontsize=7.5, color=txt_color)
fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).set_label(
    "Normalised score (0=min, 1=max)", fontsize=8)
ax.set_title(
    "Trailer Engagement by Film — Normalised (min-max) across 6 metrics",
    fontsize=10, fontweight="bold", pad=10,
)
plt.tight_layout()
fig.savefig(OUT / "views_likes_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("\\nChart saved to pandas/views_likes_heatmap.png")
'''

(PANDAS_DIR / "trailer_pandas_analysis.py").write_text(ANALYSIS_SCRIPT, encoding="utf-8")
print("✓ Saved pandas/trailer_pandas_analysis.py")

print("\n=== ALL FILES BUILT ===")
print(f"  excel/  → {list(EXCEL_DIR.glob('*.xlsx'))}")
print(f"  pandas/ → {list(PANDAS_DIR.iterdir())}")
