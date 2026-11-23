"""Compatibility entry point for raw data collection."""

from src.config import RAW_DIR, ensure_directories, load_config


def main() -> None:
    load_config()
    ensure_directories()
    print(f"Raw input directory ready: {RAW_DIR}")
    print("Populate verified API and Google Trends inputs before analysis; no data is fabricated.")


if __name__ == "__main__":
    main()
