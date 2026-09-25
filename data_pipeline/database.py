"""Normalized SQLite database creation and population.

Schema (per requirements):

    categories(category_id INTEGER PRIMARY KEY, category_name TEXT UNIQUE)
    books(book_id INTEGER PRIMARY KEY,
          title TEXT, price_gbp REAL, price_inr REAL, rating INTEGER,
          in_stock INTEGER,
          category_id INTEGER REFERENCES categories(category_id))
"""

from __future__ import annotations

import logging

import pandas as pd
from sqlite3 import connect

from . import config

logger = logging.getLogger(__name__)


def open_connection(db_path=config.DB_PATH):
    """Open a sqlite connection (creating parent directories as needed)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return connect(db_path)


def reset_schema(conn) -> None:
    """Drop existing tables so reruns are deterministic/idempotent."""
    conn.executescript(
        """
        DROP TABLE IF EXISTS books;
        DROP TABLE IF EXISTS categories;
        """
    )
    conn.commit()


def create_schema(conn) -> None:
    """Create the normalized categories + books tables."""
    conn.executescript(
        """
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY,
            category_name TEXT UNIQUE
        );

        CREATE TABLE books (
            book_id INTEGER PRIMARY KEY,
            title TEXT,
            price_gbp REAL,
            price_inr REAL,
            rating INTEGER,
            in_stock INTEGER,
            category_id INTEGER REFERENCES categories(category_id)
        );
        """
    )
    conn.commit()


def insert_categories(conn, categories: pd.Series) -> dict[str, int]:
    """Insert distinct categories and return a {name: id} mapping."""
    names = pd.unique(categories.dropna()).tolist()
    cur = conn.cursor()
    for name in names:
        cur.execute(
            "INSERT OR IGNORE INTO categories (category_name) VALUES (?)",
            (str(name),),
        )
    conn.commit()
    cur.execute("SELECT category_id, category_name FROM categories")
    mapping = {name: cid for cid, name in cur.fetchall()}
    logger.info("Categories table now has %d rows", len(mapping))
    return mapping


def insert_books(conn, books_df: pd.DataFrame, category_map: dict[str, int]) -> int:
    """Insert all cleaned book rows. Returns the number of rows inserted."""
    cur = conn.cursor()
    rows_inserted = 0
    for row in books_df.itertuples(index=False):
        category_id = category_map.get(row.category)
        if category_id is None:
            # Should not happen because Unknown is inserted, but guard anyway.
            logger.warning("No category_id for category '%s'", row.category)
            continue
        try:
            cur.execute(
                "INSERT INTO books (title, price_gbp, price_inr, rating, in_stock, category_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row.title,
                    float(row.price_gbp),
                    float(row.price_inr),
                    int(row.rating),
                    int(row.in_stock),
                    category_id,
                ),
            )
            rows_inserted += 1
        except Exception as exc:
            logger.warning("Failed to insert book '%s': %s", row.title, exc)
    conn.commit()
    logger.info("Inserted %d books into books table", rows_inserted)
    return rows_inserted


def build_database(books_df: pd.DataFrame, db_path=config.DB_PATH) -> dict:
    """Create the schema, insert categories + books, and report counts."""
    conn = open_connection(db_path)
    try:
        reset_schema(conn)
        create_schema(conn)
        category_map = insert_categories(conn, books_df["category"])
        # Ensure the placeholder category is always present.
        n_books = insert_books(conn, books_df, category_map)
        return {"db_path": str(db_path), "categories": len(category_map), "books": n_books}
    finally:
        conn.close()
