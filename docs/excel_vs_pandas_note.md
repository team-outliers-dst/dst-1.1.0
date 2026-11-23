# Spreadsheets vs Pandas — Side-by-Side Cleaning Note

**Module 1 requirement:** *Do one cleaning step in a spreadsheet, then the same step in pandas, and compare.*

---

## The cleaning step: converting `published_at` from text to date

**Source file:** `data/raw/youtube_stats.csv`  
**Column:** `published_at`  
**Raw value example:** `2025-11-18T06:50:49Z` (ISO-8601 string, UTC)  
**Goal:** convert to a usable date so we can compute how many days before its release date each trailer launched.

---

## In Excel

| # | Action | Where in Excel |
|---|--------|---------------|
| 1 | Open `youtube_stats.csv` via **Data → From Text/CSV** | Import wizard |
| 2 | In the preview, the `published_at` column appears as *General* (plain text). Click **Transform Data** to open Power Query. | Power Query Editor |
| 3 | Select the `published_at` column → **Transform → Data Type → Date/Time** | Ribbon |
| 4 | Excel's auto-detect fails on the `Z` suffix. Set locale to **English (United States)** and format `yyyy-MM-dd"T"HH:mm:ss"Z"`. | Column type dialog |
| 5 | Add a custom column `trailer_launch_date` using `=Date.From([published_at])` | Add Column → Custom Column |
| 6 | **Close & Load** to sheet. | Power Query |

**Formula alternative (without Power Query):**
```
=DATEVALUE(LEFT(A2,10))
```
Then format the cell as *Date*. The `Z` and time portion are stripped by taking only the first 10 characters.

**Result dtype in Excel:** serial date number, displayed as `18-Nov-2025`.

---

## In Pandas

```python
import pandas as pd

raw = pd.read_csv("data/raw/youtube_stats.csv")

# Before: dtype is object (string)
print(raw["published_at"].dtype)         # → object

# One-line conversion — handles timezone suffix automatically
raw["published_at"] = pd.to_datetime(
    raw["published_at"],
    errors="coerce",   # invalid strings → NaT instead of crashing
    utc=True,          # keeps the UTC timezone information
)

# After: dtype is datetime64[ns, UTC]
print(raw["published_at"].dtype)         # → datetime64[ns, UTC]

# Derive date-only column
raw["trailer_launch_date"] = raw["published_at"].dt.date
```

**Result dtype in pandas:** `datetime64[ns, UTC]`, fully arithmetic — subtraction gives `Timedelta` objects directly.

---

## Side-by-side comparison

| Aspect | Excel | Pandas |
|--------|-------|--------|
| **Raw dtype seen** | General / Text | `object` (string) |
| **Conversion method** | Power Query *Data Type* dialog, or `LEFT()` + `DATEVALUE()` | `pd.to_datetime(errors='coerce', utc=True)` |
| **Handles UTC `Z` suffix** | Only with explicit format string in Power Query | Yes, automatically |
| **Invalid values** | Shows `#VALUE!` error; must wrap every formula in `IFERROR()` | Silently become `NaT`; `errors='coerce'` is enough |
| **Time zone preserved** | No (Excel has no tz-aware date type) | Yes — `datetime64[ns, UTC]` |
| **Downstream arithmetic** | Need `DATEDIF()` or manual subtraction of serial numbers | `(release_date - published_at).dt.days` — one expression |
| **Reproducible** | No — manual click sequence, not recorded | Yes — script reruns identically from the raw CSV |
| **Effort** | ~5 minutes, 3 dialog boxes (Power Query) or a column of formulas | 1 line, < 1 second |

---

## Why this step matters for our analysis

The `published_at` date tells us when each trailer went live. The `release_date` in `movie_master.csv` tells us when the film hit theatres. Their difference — **trailer lead time** — is a confounding variable when comparing YouTube view counts: a trailer that launched 30 days before release had far more time to accumulate views than one that launched 10 days out. Without type-casting, this arithmetic is impossible.

---

## Output

The pandas-cleaned version is saved to:  
`data/cleaned/excel_vs_pandas_demo.csv`

| movie_name | trailer_launch_date | release_date | days_before_release |
|------------|--------------------:|:------------:|--------------------:|
| Dhurandhar | 2025-11-18 | 2025-12-05 | 16 |
| Chhaava | 2025-01-22 | 2025-02-14 | 22 |
| Coolie | 2025-08-02 | 2025-08-14 | 11 |
| Good Bad Ugly | 2025-04-05 | 2025-04-10 | 4 |
| Su From So | 2025-07-15 | 2025-07-25 | 9 |
| Ekka | 2025-07-11 | 2025-07-18 | 6 |
| L2: Empuraan | 2025-03-19 | 2025-03-27 | 7 |
| Lokah: Chapter 1 – Chandra | 2025-08-24 | 2025-08-28 | 3 |

> **Script:** `src/excel_vs_pandas.py` reproduces this table from the raw file in one command: `python -m src.excel_vs_pandas` from the project root.
