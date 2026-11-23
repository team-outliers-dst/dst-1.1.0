# Release Day Radar

Release Day Radar is a reproducible, exploratory analysis of online engagement
for eight Indian films: two each in Hindi, Tamil, Malayalam, and Kannada.
It investigates genre, language, TMDB metadata, YouTube trailer engagement,
Google Trends, and audience comment sentiment. Correlation is not treated as
causation, and no data is fabricated when an API or comment thread is unavailable.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `TMDB_API_KEY`, `YOUTUBE_API_KEY`, and the MySQL variables in `.env`.
Use only manually verified official trailer IDs in `data/raw/movie_master.csv`.
Export Google Trends data with the same India geography, terms, and timeframe
for all films. Download the separate IMDb 50K CSV from Kaggle; it is not merged
with the selected-film YouTube comments.

Place a Google Trends export at `data/raw/google_trends.csv`. Use the columns
defined by `google_trends_template.csv`. A common choice is one consistent
timeframe for all eight movie search terms, exported with geography `IN`.

The four batch exports are processed independently and preserved unchanged:

```text
data/raw/batch1_time_series.csv
data/raw/batch1_by_region.csv
data/raw/batch2_time_series.csv
data/raw/batch2_by_region.csv
```

Run the dedicated batch analysis with:

```powershell
python -m src.google_trends_analysis
```

The module cleans date-wise and regional exports, verifies Dhurandhar across
time-series batches, aligns Batch 2 to Batch 1 with a median anchor ratio,
preserves missing values, and keeps regional batches separate.

Configure MySQL by starting MySQL locally or through your database provider,
and set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and
`MYSQL_DATABASE` in `.env`. The pipeline creates `release_day_radar`, the three
schema tables, and available cleaned rows. Database loading can be run alone:

```powershell
python -m src.database
```

## Run

```powershell
python main.py
```

The pipeline preserves raw inputs, cleans available CSV inputs into `data/cleaned`,
calculates views/day, like rate, comment rate, and the project-defined min-max
engagement index, then writes PNG charts to `visualizations/`. If no API-derived
CSV exists, the pipeline reports that prerequisite and exits without fake output.

Individual modules can be invoked with `python -m src.data_cleaning` after adding
a module CLI, or imported from scripts. The MySQL schema is in `sql/schema.sql`
and the five required analysis queries are in `sql/analysis_queries.sql`.

## Data and evidence

The starter CSVs in `data/raw` identify the expected fields. Populate a source
register, data inventory, and cleaning log with access dates, row counts, file
sizes, data types, and decisions about missing values. Keep API JSON responses
unchanged. YouTube statistics are a retrieval snapshot; views/day adjusts for
publication age but does not recreate historical first-week performance.

The project has the three Big Data Vs: volume across APIs and the separate 50K
review corpus, velocity from changing YouTube metrics/comments, and variety across
JSON, CSV, and free text. The eight-film sample is small, language-balanced but
not genre-balanced, platform-specific, multilingual, and vulnerable to promotion
spend, bots, inaccessible comments, API quotas, and selection bias.

## Structure

`src/` contains collection, cleaning, feature engineering, database, sentiment,
PySpark, EDA, and visualisation modules. `data/raw` is immutable source input;
`data/cleaned` contains transformations. `.env` is ignored and must never be
committed.
