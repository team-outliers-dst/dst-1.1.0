"""Project paths and environment-backed configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
VISUALIZATIONS_DIR = ROOT_DIR / "visualizations"
LOG_DIR = ROOT_DIR / "logs"

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "release_day_radar")


def load_config() -> None:
    """Load optional .env values after module import."""
    load_dotenv(ROOT_DIR / ".env")
    for name, default in (
        ("TMDB_API_KEY", ""),
        ("YOUTUBE_API_KEY", ""),
        ("MYSQL_HOST", "localhost"),
        ("MYSQL_PORT", "3306"),
        ("MYSQL_USER", "root"),
        ("MYSQL_PASSWORD", ""),
        ("MYSQL_DATABASE", "release_day_radar"),
    ):
        value = os.getenv(name, default)
        globals()[name] = int(value) if name == "MYSQL_PORT" else value


def ensure_directories() -> None:
    for directory in (RAW_DIR, CLEANED_DIR, VISUALIZATIONS_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)
