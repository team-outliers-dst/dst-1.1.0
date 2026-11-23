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

print("\nLanguage summary:")
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
print("\nChart saved to pandas/views_likes_heatmap.png")
