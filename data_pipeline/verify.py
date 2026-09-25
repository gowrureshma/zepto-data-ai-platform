"""Verify the SQL JOIN result against an equivalent pandas.merge.

Steps:
    1. Read the ``books`` and ``categories`` tables into DataFrames using
       ``pandas.read_sql`` (two queries via read_sql as required).
    2. Run the JOIN query through ``pandas.read_sql`` to get the reference
       result.
    3. Reproduce the same JOIN with ``pandas.merge`` on in-memory DataFrames.
    4. Compare the two result sets for equality.
"""

from __future__ import annotations

import json
import logging

import pandas as pd
import sqlite3

from . import config

logger = logging.getLogger(__name__)

JOIN_SQL = """
    SELECT b.book_id, b.title, b.price_gbp, b.price_inr, b.rating,
           b.in_stock, b.category_id, c.category_name
    FROM books b
    JOIN categories c ON b.category_id = c.category_id
    ORDER BY b.book_id
"""

RESULT_COLUMNS = [
    "book_id", "title", "price_gbp", "price_inr", "rating",
    "in_stock", "category_id", "category_name",
]


def verify_join(db_path=config.DB_PATH, out_path=config.JOIN_COMPARISON_PATH) -> dict:
    """Run the SQL JOIN and the pandas.merge equivalent, then compare."""
    conn = sqlite3.connect(db_path)

    # Read at least two SQL query results using pandas.read_sql.
    df_books = pd.read_sql_query("SELECT * FROM books", conn)
    df_categories = pd.read_sql_query("SELECT * FROM categories", conn)

    # Reference result: the JOIN executed in SQL.
    df_sql = pd.read_sql_query(JOIN_SQL, conn)
    conn.close()

    # Reproduce the JOIN with pandas.merge on in-memory DataFrames.
    df_pandas = df_books.merge(df_categories, on="category_id", how="inner")

    # Align column order so the two frames are directly comparable.
    df_sql = df_sql[RESULT_COLUMNS].sort_values("book_id").reset_index(drop=True)
    df_pandas = df_pandas[RESULT_COLUMNS].sort_values("book_id").reset_index(drop=True)

    # Compare values (ignore dtype differences from read_sql).
    try:
        pd.testing.assert_frame_equal(
            df_sql, df_pandas, check_dtype=False, check_like=True
        )
        match = True
        difference = "SQL JOIN and pandas.merge results are equal (row-for-row)."
    except AssertionError as exc:
        match = False
        difference = str(exc)

    report = {
        "sql_join_rows": int(len(df_sql)),
        "pandas_merge_rows": int(len(df_pandas)),
        "columns": RESULT_COLUMNS,
        "match": match,
        "difference": difference,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Saved JOIN comparison report to %s", out_path)
    logger.info("JOIN verification -> match=%s (sql=%d rows, pandas=%d rows)",
                match, report["sql_join_rows"], report["pandas_merge_rows"])
    return report
