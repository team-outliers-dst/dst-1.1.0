# Excel vs Pandas — Full Comparison Report

**Case Study A: Release Day Radar**  
**Module 1 topic: Spreadsheets and Dataframes**  
**Dataset:** YouTube trailer statistics for 8 Indian film releases (2025–26)

---

## 1. Objective

The brief requires doing **one cleaning step in a spreadsheet, then the same step in pandas, and comparing**. This report documents that comparison end-to-end, from raw file to aggregated pivot, using `data/raw/youtube_stats.csv` as the shared starting point.

The cleaning step chosen is:

> **Type-casting `published_at` from an ISO-8601 text string to a usable date**, so that trailer lead time (days between trailer launch and release date) can be computed arithmetically.

This step was selected because it is *necessary* for the core analysis (trailer lead time as a predictor of views), and it exposes a real behavioural difference between Excel and pandas.

---

## 2. The Raw Data

**File:** `data/raw/youtube_stats.csv`  
**Rows:** 8 (one per film trailer)  
**Relevant columns:**

| Column | Raw value example | Raw dtype in Excel | Raw dtype in pandas |
|--------|------------------|--------------------|---------------------|
| `published_at` | `2025-11-18T06:50:49Z` | General (plain text) | `object` (string) |
| `views` | `101925598` | Number | `int64` |
| `likes` | `914697` | Number | `int64` |
| `release_date` | `2025-12-05` | General / Text | `object` (string) |

Both tools read `published_at` as text. Neither can do date arithmetic on it without an explicit conversion step.

---

## 3. Step-by-Step: In Excel

**File produced:** `excel/Trailer_Engagement_Analysis.xlsx` (sheets: *Raw Data*, *Typed & Cleaned*, *Pivot — Language Summary*)

### 3.1 Open the file

1. Open `data/raw/youtube_stats.csv` via **Data → From Text/CSV**.
2. In the import wizard the `published_at` column appears as *General* — Excel treats the ISO-8601 string as plain text.

### 3.2 Convert `published_at` to a date

**Option A — Power Query (recommended):**
1. Click **Transform Data** to open Power Query Editor.
2. Select the `published_at` column → **Transform → Data Type → Date/Time**.
3. Set the locale to **English (United States)** and the format to `yyyy-MM-dd"T"HH:mm:ss"Z"`.
4. Add a custom column:
   ```
   = Date.From([published_at])
   ```
5. **Close & Load** to sheet.

**Option B — Formula (single column):**
```excel
=DATEVALUE(LEFT(A2,10))
```
Then format the cell as *Date*. This strips the time and UTC suffix by taking the first 10 characters.

> ⚠ **Pitfall:** Excel has no native UTC-aware datetime type. The UTC offset (`Z`) is discarded by both methods. This is not a problem for computing day-level lag but would matter for sub-daily analysis.

### 3.3 Compute `days_before_release`

In a new column, subtract the typed trailer date from the release date:
```excel
=release_date - trailer_launch_date
```
Format as *Number* (not Date). Result is an integer count of days.

### 3.4 Pivot table (Language Summary)

**Insert → PivotTable**, with:
- **Rows:** Language
- **Values:** Average of Views, Average of Likes, Average of Like Rate, Average of Days Before Release

This is reproduced exactly in `excel/excel_pivot_values.xlsx`.

---

## 4. Step-by-Step: In Pandas

**Script:** `pandas/trailer_pandas_analysis.py`  
**Run from project root:** `python pandas/trailer_pandas_analysis.py`

### 4.1 Load

```python
import pandas as pd

raw    = pd.read_csv("data/raw/youtube_stats.csv")
master = pd.read_csv("data/raw/movie_master.csv", skiprows=1)
master["release_date"] = pd.to_datetime(master["release_date"])
```

### 4.2 Type-cast `published_at`

```python
# Before: dtype is object (string)
print(raw["published_at"].dtype)       # → object

raw["published_at"] = pd.to_datetime(
    raw["published_at"],
    errors="coerce",   # invalid strings → NaT  (not a crash)
    utc=True,          # keeps UTC timezone information
)

# After: dtype is datetime64[ns, UTC]
print(raw["published_at"].dtype)       # → datetime64[ns, UTC]
```

### 4.3 Derive `days_before_release`

```python
df = raw.merge(master[["movie_id","language","release_date"]], on="movie_id", how="left")

df["trailer_launch_date"] = df["published_at"].dt.date
df["days_before_release"] = (
    df["release_date"] - df["published_at"].dt.tz_localize(None)
).dt.days
```

### 4.4 Pivot (Language Summary)

```python
lang_df = df.groupby("language").agg(
    films                  =("movie_name",        "count"),
    total_views            =("views",             "sum"),
    avg_views              =("views",             "mean"),
    avg_like_rate_pct      =("like_rate",         "mean"),
    avg_days_before_release=("days_before_release","mean"),
).round(0).reset_index()
```

---

## 5. Per-Film Results (output of both tools, identical values)

**File:** `pandas/engagement_by_film.csv`

| Film | Language | Days Before Release | Views | Like Rate % |
|------|----------|--------------------:|------:|------------:|
| Dhurandhar | Hindi | 16 | 101,925,598 | 0.90 |
| Chhaava | Hindi | 22 | 81,723,957 | 1.52 |
| Coolie | Tamil | 11 | 29,538,577 | 2.84 |
| Good Bad Ugly | Tamil | 4 | 2,910,005 | 3.17 |
| Su From So | Kannada | 9 | 7,167,108 | 1.41 |
| Ekka | Kannada | 6 | 2,932,601 | 3.07 |
| L2: Empuraan | Malayalam | 7 | 17,681,677 | 3.10 |
| Lokah: Chapter 1 – Chandra | Malayalam | 3 | 16,308,431 | 1.22 |

---

## 6. Language Pivot (output of both tools, identical values)

**File:** `pandas/engagement_by_language.csv` / `excel/excel_pivot_values.xlsx`

| Language | # Films | Avg Views | Avg Like Rate % | Avg Days Before Release |
|----------|--------:|----------:|----------------:|------------------------:|
| Hindi | 2 | 91,824,778 | 1.0% | 19 |
| Kannada | 2 | 5,049,854 | 2.0% | 8 |
| Malayalam | 2 | 16,995,054 | 2.0% | 5 |
| Tamil | 2 | 16,224,291 | 3.0% | 8 |

---

## 7. Side-by-Side Comparison

**File:** `pandas/excel_pandas_difference.csv` (all delta columns = 0.0)

| Aspect | Excel | Pandas |
|--------|-------|--------|
| **Raw dtype of `published_at`** | General (text) | `object` (string) |
| **Conversion method** | Power Query *Data Type* dialog, or `=DATEVALUE(LEFT(A2,10))` | `pd.to_datetime(errors='coerce', utc=True)` |
| **Handles UTC `Z` suffix** | Only with explicit format string in Power Query | Yes, automatically |
| **Invalid / unparseable values** | Shows `#VALUE!` — must wrap each formula in `IFERROR()` | Silently become `NaT`; `errors='coerce'` is enough |
| **Timezone preserved** | ❌ No (Excel has no tz-aware datetime type) | ✅ Yes — `datetime64[ns, UTC]` |
| **Day-lag arithmetic** | `=DATEDIF(trailer_launch, release_date, "D")` or `=release−launch` with Number format | `(release_date − published_at.dt.tz_localize(None)).dt.days` |
| **Pivot / aggregation** | Insert → PivotTable, drag fields | `df.groupby().agg()` or `df.pivot_table()` |
| **Pivot values match?** | — | ✅ All deltas = 0.0 (confirmed in `excel_pandas_difference.csv`) |
| **Null-safe?** | ❌ No — `IFERROR()` per cell required | ✅ Yes — `NaT` propagates gracefully |
| **Reproducible?** | ❌ No — manual click sequence, not version-controlled | ✅ Yes — script reruns identically from raw CSV |
| **Time to run** | ~5 min (Power Query) or manual formula column | ~1 second |
| **Output files** | `excel/Trailer_Engagement_Analysis.xlsx` | `pandas/engagement_by_film.csv`, `engagement_by_language.csv`, `trailer_lag_pivot.csv` |

---

## 8. Visualisation: Normalised Engagement Heatmap

**File:** `pandas/views_likes_heatmap.png`

The heatmap normalises all six metrics (views, likes, comments, like rate, comment rate, days before release) to a 0–1 scale using min-max normalisation, so films of wildly different scale can be visually compared on one chart. Each cell shows the actual raw value; colour encodes the relative rank within that metric.

**Key observation from the chart:** Hindi films (Dhurandhar, Chhaava) dominate raw view counts but have the *lowest* like rates (~1%), while Tamil and Kannada films show the highest like rates (~3%) despite far lower absolute view counts. This suggests language audience size and engagement intensity are independent dimensions — raw view count alone is a misleading proxy for buzz quality.

---

## 9. Why the Pivot Values Are Identical

The delta CSV (`pandas/excel_pandas_difference.csv`) shows all delta columns as `0.0`. This is expected: both tools compute a simple `mean()` over integer values. The purpose of the difference file is to demonstrate the *process* of verification — in a larger or messier dataset, floating-point rounding differences or formula errors in Excel would surface here.

---

## 10. Files Summary

```
excel/
├── Trailer_Engagement_Analysis.xlsx    ← 3 sheets: Raw Data / Typed & Cleaned / Pivot
└── excel_pivot_values.xlsx             ← pivot only, for direct comparison

pandas/
├── trailer_pandas_analysis.py          ← standalone runnable script
├── engagement_by_film.csv              ← per-film typed + derived columns
├── engagement_by_language.csv          ← language-level aggregation
├── trailer_lag_pivot.csv               ← full pivot_table() output
├── excel_pandas_difference.csv         ← side-by-side + delta columns
└── views_likes_heatmap.png             ← normalised heatmap visualisation

docs/
├── excel_vs_pandas_note.md             ← brief side-by-side note (brief requirement)
└── excel_vs_pandas_report.md           ← this full report
```

> **Brief requirement met:** One cleaning step (type-casting `published_at`) done in Excel (documented above and in the `.xlsx` file) and in pandas (script + CSVs), with a short side-by-side note (`docs/excel_vs_pandas_note.md`) and this full report as evidence.
