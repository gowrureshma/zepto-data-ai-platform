"""End-to-end orchestrator for Module 1: Data Pipeline.

Run from the repository root:
    python -m data_pipeline.pipeline

This single command scrapes books.toscrape.com, cleans the data, builds a
normalized SQLite database, runs SQL queries, and verifies the SQL JOIN
against an equivalent pandas.merge -- with no manual copy/paste.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow execution both as `python -m data_pipeline.pipeline` and as a script.
if __package__ in (None, ""):  # pragma: no cover - invocation convenience
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "data_pipeline"

from . import config
from .scraper import scrape_catalogue, save_raw
from .cleaner import clean_books, save_cleaned
from .database import build_database
from .queries import run_queries, print_query_summary
from .verify import verify_join

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("data_pipeline")


def main() -> int:
    logger.info("=== Module 1: Data Pipeline ===")
    logger.info("Source: %s (%d catalogue pages)", config.BASE_URL, config.NUM_PAGES)
    logger.info("Exchange rate: 1 GBP = %.2f INR (fixed)", config.GBP_TO_INR)

    # 1. Scrape
    books = scrape_catalogue(pages=config.NUM_PAGES)
    if not books:
        logger.error("Scraping returned no books; aborting.")
        return 1
    save_raw(books, config.RAW_BOOKS_PATH)

    # 2. Clean
    cleaned = clean_books(books)
    if cleaned.empty:
        logger.error("No books survived cleaning; aborting.")
        return 1
    save_cleaned(cleaned, config.CLEANED_BOOKS_CSV)

    # 3. Build SQLite database
    db_info = build_database(cleaned, config.DB_PATH)

    # 4. Run SQL queries
    query_results = run_queries(config.DB_PATH, config.SQL_OUTPUTS_PATH)
    print_query_summary(query_results)

    # 5. Verify JOIN vs pandas.merge
    verification = verify_join(config.DB_PATH, config.JOIN_COMPARISON_PATH)

    # ---- Summary report ----
    summary = {
        "books_scraped": len(books),
        "books_cleaned": len(cleaned),
        "categories": db_info["categories"],
        "database": db_info["db_path"],
        "queries_executed": len(query_results),
        "join_match": verification["match"],
    }
    logger.info("=== Pipeline complete ===")
    for key, value in summary.items():
        logger.info("%s: %s", key, value)
    logger.info("Database: %s", config.DB_PATH)
    logger.info("SQL outputs: %s", config.SQL_OUTPUTS_PATH)
    logger.info("JOIN comparison: %s", config.JOIN_COMPARISON_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
