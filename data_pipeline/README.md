# Module 1 — Data Pipeline

A modular ETL pipeline that scrapes [books.toscrape.com](https://books.toscrape.com/),
cleans the data, loads it into a normalized SQLite database, runs SQL queries,
and verifies the SQL `JOIN` result against an equivalent `pandas.merge`.

> This is **only Module 1** of the Zepto Data & AI Platform capstone.
> `analytics` and `support_assistant` are intentionally left untouched.

## What it does

1. **Source** — [`https://books.toscrape.com/`](https://books.toscrape.com/)
2. **Scrape** — the first **5 pages** of the *All Products* catalogue
   (`catalogue/page-1.html` … `page-5.html`). Each page lists 20 books, yielding
   ~100 books (≥ 60 required). For each book the following is collected:
   - `title`
   - `price` (GBP string, e.g. `£51.77`)
   - `star_rating` (`One`/`Two`/`Three`/`Four`/`Five`)
   - `availability` (`instock` / `outofstock`)
   - `category` (read from the book's detail-page breadcrumb, since the listing
     page does not expose it)
3. **Clean** (with `pandas`):
   - `price` → `price_gbp` (`float`)
   - `star_rating` → `rating` (`int`, 1–5)
   - `availability` → `in_stock` (`int`, 0/1)
   - `price_inr = price_gbp * 105.50` — **fixed** rate, not a live rate
   - parsing failures are handled safely (no crash); rows with missing essential
     fields are dropped and logged
4. **Load** into a normalized SQLite database (`output/data/books.db`):

   | table       | columns                                                                                       |
   |-------------|-----------------------------------------------------------------------------------------------|
   | `categories`| `category_id` (PK), `category_name` (UNIQUE)                                                  |
   | `books`     | `book_id` (PK), `title`, `price_gbp`, `price_inr`, `rating`, `in_stock`, `category_id` (FK)   |
5. **Query** — runs 7 SQL queries demonstrating `SELECT`, `WHERE`, `ORDER BY`,
   `LIMIT`, `DISTINCT`, `IN`, `BETWEEN`, and `JOIN`. Outputs are saved to
   `output/results/sql_query_outputs.txt`.
6. **Verify** — reads the `books` and `categories` tables via `pandas.read_sql`
   (two SQL reads), reproduces the `JOIN` query's result from SQL, reproduces the
   same join in-memory with `pandas.merge`, and asserts the two result sets match.
   Report saved to `output/results/join_comparison.json`.

## Project layout

```
data_pipeline/
├── __init__.py        # package marker
├── config.py          # constants: URLs, exchange rate, paths
├── scraper.py         # scraping (listing pages + detail-page categories)
├── cleaner.py         # price/rating/availability conversion + INR
├── database.py        # normalized SQLite schema + inserts
├── queries.py         # 7 SQL queries, execution, and text output
├── verify.py          # SQL JOIN vs pandas.merge verification
├── pipeline.py        # orchestrator — the single entry point
├── requirements.txt   # Python dependencies
├── README.md          # this file
└── output/            # generated (gitignored)
    ├── data/
    │   ├── raw_books.json
    │   ├── cleaned_books.csv
    │   └── books.db
    └── results/
        ├── sql_query_outputs.txt
        └── join_comparison.json
```

## Requirements

- Python 3.10+
- `requests`, `beautifulsoup4`, `pandas`
- `sqlite3` (part of the Python standard library)

Install dependencies:

```bash
python -m pip install -r data_pipeline/requirements.txt
```

## How to run

From the **repository root**:

```bash
python -m data_pipeline.pipeline
```

That runs the entire pipeline end-to-end (scrape → clean → database → queries →
verification) with no manual steps.

You can also run it directly as a script:

```bash
python data_pipeline/pipeline.py
```

The script is safe to re-run; it wipes and rebuilds the SQLite database each time.

## Configuration

Edit `data_pipeline/config.py` to change:

| constant            | default                              | meaning                              |
|---------------------|--------------------------------------|--------------------------------------|
| `NUM_PAGES`         | `5`                                  | catalogue pages to scrape            |
| `GBP_TO_INR`        | `105.50` (fixed rate)                | INR per GBP                          |
| `MAX_DETAIL_WORKERS`| `8`                                  | threads for detail-page category fetch |

## Outputs (all under `data_pipeline/output/`, gitignored)

- `data/raw_books.json` — raw records scraped from the site
- `data/cleaned_books.csv` — cleaned tabular data
- `data/books.db` — normalized SQLite database
- `results/sql_query_outputs.txt` — all SQL queries and their actual outputs
- `results/join_comparison.json` — SQL JOIN vs `pandas.merge` match report
