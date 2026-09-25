"""Central configuration for the data pipeline Module 1.

All tunable constants live here so the rest of the package stays free of
hard-coded values.
"""

# ---------------------------------------------------------------------------
# Scraping source
# ---------------------------------------------------------------------------
# Source: https://books.toscrape.com/
# We scrape the first N pages of the "All Products" catalogue. Each catalogue
# page lists 20 books, so NUM_PAGES=5 yields ~100 books (>= 60 required).
BASE_URL = "http://books.toscrape.com/"
CATALOGUE_PAGE_URL = BASE_URL + "catalogue/page-{page}.html"
NUM_PAGES = 5
REQUEST_TIMEOUT = 15
MAX_DETAIL_WORKERS = 8

# ---------------------------------------------------------------------------
# Currency conversion (FIXED rate - NOT a live exchange rate)
# Requirement: 1 GBP = 105.50 INR
# ---------------------------------------------------------------------------
GBP_TO_INR = 105.50

# ---------------------------------------------------------------------------
# Output locations (all generated artefacts live under data_pipeline/output)
# ---------------------------------------------------------------------------
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PACKAGE_DIR / "output"
DATA_DIR = OUTPUT_DIR / "data"
RESULTS_DIR = OUTPUT_DIR / "results"

RAW_BOOKS_PATH = DATA_DIR / "raw_books.json"
CLEANED_BOOKS_CSV = DATA_DIR / "cleaned_books.csv"
DB_PATH = DATA_DIR / "books.db"

SQL_OUTPUTS_PATH = RESULTS_DIR / "sql_query_outputs.txt"
JOIN_COMPARISON_PATH = RESULTS_DIR / "join_comparison.json"
