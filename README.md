# Release Day Radar - Case Study A

Release Day Radar is a reproducible, exploratory analysis of online engagement for eight Indian films, with two films each in Hindi, Tamil, Malayalam, and Kannada. The project combines film metadata, official YouTube trailer performance, Google Trends search interest, and audience-comment sentiment to explore how language, genre, cast popularity, ratings, search behaviour, and audience reactions relate to online engagement.

The selected-film analysis uses TMDB, YouTube Data API, and manually exported Google Trends data. A separate IMDb 50K review corpus is processed with PySpark as supplementary large-scale text data; it is **not** merged with comments from the eight selected films. The analysis is descriptive: observed associations are not interpreted as causal effects.

---

## Research Questions

- How does trailer engagement vary across film languages and genres?
- How are TMDB metadata, including ratings and lead-cast popularity, associated with trailer views and engagement?
- How does Google Trends search interest vary across the selected films, and how does it relate to observed trailer engagement?
- What sentiment and recurring discussion topics appear in publicly accessible comments on verified official trailers?
- What additional text-level patterns can be explored in the separate IMDb 50K review corpus?

---

## Repository Layout

```
dst-1.1.0/
├── data/
│   ├── raw/                         # Source inputs and API exports
│   │   ├── movie_master.csv         # Eight-film master list and verified trailer IDs
│   │   ├── tmdb_movies.json         # Preserved TMDB API responses
│   │   ├── tmdb_movies.csv          # Flattened TMDB metadata
│   │   ├── youtube_stats.csv        # YouTube trailer statistics snapshot
│   │   ├── youtube_comments.csv     # Retrieved public trailer comments
│   │   ├── batch1_time_series.csv   # Google Trends time-series export
│   │   ├── batch1_by_region.csv     # Google Trends regional export
│   │   ├── batch2_time_series.csv   # Second Google Trends time-series export
│   │   └── batch2_by_region.csv     # Second Google Trends regional export
│   └── cleaned/                     # Generated cleaned and analysis-ready data
│
├── src/
│   ├── config.py                    # Paths, environment variables, configuration
│   ├── data_collection.py           # TMDB and YouTube collection coordinator
│   ├── tmdb_collector.py             # TMDB metadata retrieval and flattening
│   ├── youtube_collector.py          # Trailer statistics and comment retrieval
│   ├── data_cleaning.py               # Cleaning and audit-log generation
│   ├── feature_engineering.py         # Views/day, rates, engagement index
│   ├── exploratory_analysis.py        # Descriptive summaries and correlations
│   ├── sentiment_analysis.py          # VADER sentiment and keyword topics
│   ├── google_trends_analysis.py      # Trends cleaning, batch alignment, charts
│   ├── pyspark_analysis.py            # Separate IMDb 50K corpus analysis
│   ├── database.py                    # MySQL schema creation and data loading
│   ├── data_inventory.py              # Data inventory and source register
│   └── visualizations.py               # Engagement and sentiment charts
│
├── sql/
│   ├── schema.sql                     # Normalised MySQL schema (3 tables)
│   └── analysis_queries.sql           # Five analytical SQL queries
│
├── visualizations/                    # Generated PNG charts
├── logs/                              # Generated cleaning and processing logs
├── main.py                            # Main end-to-end analysis pipeline
├── requirements.txt                   # Python dependencies
├── .env.example                       # API and MySQL configuration template
└── README.md
```

Generated files under `data/cleaned/`, `visualizations/`, and `logs/` are created as the pipeline runs. The raw source files should be treated as inputs and preserved.

---

## Data Sources

| Dataset | Source | Coverage / Sample | Granularity |
| --- | --- | --- | --- |
| Film metadata | TMDB API | Eight selected Indian films | One record per film |
| Trailer statistics | YouTube Data API | Manually verified official trailers | Retrieval-time snapshot per video |
| Trailer comments | YouTube Data API | Publicly accessible comments on selected trailers | Comment-level |
| Search interest | Google Trends (India) | Eight film search terms; manually exported in two batches | Date-wise relative interest (0–100) |
| Regional search interest | Google Trends (India) | Regional interest for exported terms | Region-wise relative interest |
| Supplementary reviews | IMDb 50K dataset (Kaggle) | Separate general movie-review corpus | Review-level |

The selected-film sample contains two films in each of four languages: Hindi, Tamil, Kannada, and Malayalam. The film master list and manually verified YouTube video IDs are maintained in `data/raw/movie_master.csv`.

Google Trends values represent relative search interest, not absolute search counts. Keep geography, search terms, and timeframe consistent when exporting batches. The IMDb 50K dataset is supplementary and must not be presented as comments or reviews of the eight selected films.

---

## Tools Used

| Tool | Script / File | What it produces |
| --- | --- | --- |
| **TMDB API** | `src/tmdb_collector.py` | Film metadata, genre, runtime, ratings, votes, and cast information |
| **YouTube Data API** | `src/youtube_collector.py` | Trailer statistics and publicly accessible comments |
| **pandas** | `src/data_cleaning.py`, `src/feature_engineering.py`, `src/exploratory_analysis.py` | Cleaned datasets, engagement metrics, grouped summaries, and correlations |
| **VADER** | `src/sentiment_analysis.py` | Comment sentiment scores and positive/neutral/negative labels |
| **Keyword classification** | `src/sentiment_analysis.py` | Rule-based comment topics: Acting, Music, Visuals, Story, Direction, and General |
| **Google Trends** | `src/google_trends_analysis.py` | Cleaned time-series and regional exports, batch comparison, aligned interest data, and charts |
| **PySpark** | `src/pyspark_analysis.py` | Text-cleaning and review-length summaries for the separate IMDb 50K corpus |
| **MySQL** | `sql/schema.sql`, `sql/analysis_queries.sql` | Relational storage for films, trailer statistics, and comments; five analytical queries |
| **matplotlib / seaborn** | `src/visualizations.py`, `src/google_trends_analysis.py` | PNG visualisations of engagement, metadata relationships, sentiment, and search interest |

---

## Quickstart

> **Prerequisites:** Python 3.10+, pip, API credentials for TMDB and YouTube, and MySQL 8+ if database loading is required. Java is required to run the optional PySpark analysis.

### 1. Clone the repository and install dependencies

```bash
git clone https://github.com/team-outliers-dst/dst-1.1.0.git
cd dst-1.1.0

python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install the Python packages:

```bash
pip install -r requirements.txt
```

### 2. Configure API keys and database credentials

Create a local environment file:

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

Set the following values in `.env`:

```env
TMDB_API_KEY=your_tmdb_api_key
YOUTUBE_API_KEY=your_youtube_api_key

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=release_day_radar
```

Keep `.env` private. Do not commit API keys or database passwords.

### 3. Verify the film master list

Review `data/raw/movie_master.csv` before collection. It contains the eight selected films and their manually verified official YouTube trailer IDs. Collection is restricted to rows marked as verified. Do not substitute unofficial uploads or guessed video IDs.

### 4. Collect TMDB and YouTube data

With API credentials configured, run:

```bash
python -m src.data_collection
```

The collection module retrieves TMDB metadata and YouTube trailer statistics/comments for verified videos. It preserves the TMDB response payload in JSON and writes tabular exports under `data/raw/`. YouTube statistics are a snapshot taken at retrieval time.

### 5. Prepare Google Trends exports

Export the time-series and regional data from Google Trends for the selected film search terms. Use India as the geography and keep the terms and comparison settings consistent across batches.

Place the four exports in `data/raw/`:

```text
data/raw/batch1_time_series.csv
data/raw/batch1_by_region.csv
data/raw/batch2_time_series.csv
data/raw/batch2_by_region.csv
```

Run the dedicated analysis:

```bash
python -m src.google_trends_analysis
```

The module cleans date-wise and regional exports independently, compares the overlapping Dhurandhar anchor series, calculates a median scale ratio when needed, and aligns Batch 2 to the Batch 1 reference scale. Missing values, including Google Trends values represented as `<1`, are retained as missing rather than converted to fabricated zeroes. Regional batches remain separate.

### 6. Run the main analysis pipeline

```bash
python main.py
```

The pipeline generates a data inventory and source register, cleans available raw CSV inputs, calculates engagement metrics, creates descriptive summaries, analyses comments when available, and saves charts under `visualizations/`. If the four Google Trends batch files are present, the batch analysis is also triggered.

If no cleaned YouTube statistics are available, the pipeline reports the missing prerequisite and exits without generating fabricated engagement results.

### 7. Load the MySQL database

Start your MySQL server and confirm the connection settings in `.env`. The main pipeline attempts to create the schema and load available cleaned data. The database module can also be used independently from Python:

```python
from pathlib import Path
from src.database import create_schema, load_cleaned_data
from src.config import CLEANED_DIR

root = Path.cwd()
create_schema(root / "sql" / "schema.sql")
load_cleaned_data(
    CLEANED_DIR / "movie_engagement.csv",
    CLEANED_DIR / "analysed_comments.csv",
)
```

The schema creates three related tables: `films`, `trailer_stats`, and `comments`. The five queries in `sql/analysis_queries.sql` cover film records, average views/day by genre and language, cast-popularity comparisons, and comment sentiment counts.

### 8. Run the optional IMDb 50K PySpark analysis

Download the IMDb 50K movie-review CSV from the Kaggle source listed above. This dataset is not included in the selected-film YouTube comment analysis.

Invoke the analysis function with the input CSV and an output directory:

```python
from src.pyspark_analysis import run_imdb_analysis

run_imdb_analysis(
    input_path="path/to/IMDB Dataset.csv",
    output_path="outputs/imdb_sentiment_summary",
)
```

The PySpark job removes HTML tags, derives review length and word count, and writes review-count and text-length summaries grouped by the dataset's sentiment label. It checks that at least 50,000 records were processed.

---

## Analysis Outputs

The pipeline derives the following measures and outputs when the corresponding source data is available:

- **Views per day:** Total trailer views divided by the number of days between publication and retrieval, with a minimum one-day denominator.
- **Like rate:** Likes as a percentage of views.
- **Comment rate:** Comment count as a percentage of views.
- **Engagement index:** A project-defined min-max normalised composite: 50% views/day, 25% like rate, and 25% comment rate.
- **Sentiment:** VADER compound scores mapped to positive, neutral, or negative labels.
- **Comment topics:** Transparent keyword-based categories for Acting, Music, Visuals, Story, Direction, and General.
- **Google Trends:** Cleaned monthly/date-wise interest, regional exports, batch-anchor comparison, and peak-interest periods.
- **IMDb review summary:** Review counts and average text length/word count by sentiment label, generated separately with PySpark.

### Generated charts

Depending on which inputs are available, the visualisation module can generate:

- `genre_vs_engagement.png`
- `language_vs_views_per_day.png`
- `cast_vs_views.png`
- `rating_vs_engagement.png`
- `google_trends_vs_engagement.png`
- `comment_topics_vs_sentiment.png`

The Google Trends module also generates monthly search-interest and regional comparison charts under `visualizations/`.

These are analysis outputs, not pre-asserted findings. Numerical conclusions should be reported only after running the pipeline on the corresponding retrieved datasets.

---

## Data Quality and Methodological Notes

- **Raw-data preservation:** Raw source inputs and API responses should remain unchanged. Cleaning and derived features are written separately under `data/cleaned/`.
- **Verified trailers only:** YouTube collection uses manually verified official trailer IDs from the film master file.
- **Retrieval snapshots:** YouTube views, likes, and comment counts reflect the time of collection. Views/day adjusts for publication age but cannot reconstruct historical first-week performance.
- **Missing data:** Unavailable API responses, inaccessible comment threads, and missing values are not replaced with invented observations.
- **Google Trends scaling:** Search-interest scores are relative and normalised. Batch alignment uses the overlapping Dhurandhar series as an anchor; it does not convert interest scores into absolute search volume.
- **Separate review corpus:** IMDb 50K reviews are supplementary general movie reviews. They are not attributed to the eight selected films and are not merged with YouTube comments.
- **Sentiment limitations:** VADER is a lexicon-based sentiment tool and may not reliably capture sarcasm, code-switching, transliteration, or nuanced multilingual expressions. Topic labels are keyword-based rather than learned categories.
- **Sampling limitations:** Eight films provide a small, language-balanced but not necessarily genre-balanced sample. Results are platform-specific and may be affected by release timing, marketing spend, cast popularity, bots, API quotas, and comment availability.
- **Interpretation:** Correlation and descriptive comparisons do not establish causation. The engagement index is a project-defined composite for exploratory comparison, not an industry-standard measure.

---

## References

- [TMDB API documentation](https://developer.themoviedb.org/docs)
- [YouTube Data API documentation](https://developers.google.com/youtube/v3)
- [Google Trends](https://trends.google.com/trends/)
- [IMDb 50K Movie Reviews dataset on Kaggle](https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews)

---

## Security

- Store API keys and database credentials only in the local `.env` file.
- Never commit `.env`, access tokens, or private credentials.
- Keep raw source files distinct from cleaned and derived outputs.
