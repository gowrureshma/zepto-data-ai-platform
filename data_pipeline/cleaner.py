"""Data cleaning for scraped books.

Produces a tidy pandas DataFrame with the final columns:
    title, price_gbp, price_inr, rating, in_stock, category

Conversions (per requirements):
    * price_str "£51.77" -> price_gbp float
    * star_rating One/Two/.../Five -> rating int (1..5)
    * availability_class instock/outofstock -> in_stock bool (stored as 0/1)
    * price_inr = price_gbp * 105.50  (FIXED rate, not live)
"""

from __future__ import annotations

import logging

import pandas as pd

from . import config

logger = logging.getLogger(__name__)

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_price(price_str: str) -> float | None:
    """Convert a "£12.99" string into a float, or None on failure."""
    if not price_str:
        return None
    try:
        return float(str(price_str).replace("£", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def parse_rating(star_class: str) -> int | None:
    """Convert a star-rating word into an integer 1-5."""
    return RATING_MAP.get(star_class, None)


def parse_in_stock(availability_class: str, availability_text: str) -> bool | None:
    """Convert availability into a boolean in_stock flag."""
    if availability_class == "instock":
        return True
    if availability_class == "outofstock":
        return False
    if availability_class == "":
        text = (availability_text or "").lower()
        if "in stock" in text and "out of stock" not in text:
            return True
        if "out of stock" in text:
            return False
    return None


def clean_books(books: list[dict]) -> pd.DataFrame:
    """Clean raw scraped book dicts into a validated DataFrame."""
    if not books:
        logger.warning("No books to clean; returning empty DataFrame")
        return pd.DataFrame(
            columns=["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]
        )

    df = pd.DataFrame(books)

    # price_gbp: strip currency symbol and coerce to float (NaN on failure)
    price_src = (
        df["price_str"]
        .astype(str)
        .str.replace("£", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["price_gbp"] = pd.to_numeric(price_src, errors="coerce")

    # rating: One..Five -> 1..5 (NaN on failure)
    df["rating"] = pd.to_numeric(df["star_rating"].map(RATING_MAP), errors="coerce")

    # in_stock: instock/outofstock -> 1/0 via nullable Int64 (NaN on failure)
    df["in_stock"] = df.apply(
        lambda row: parse_in_stock(row["availability_class"], row["availability_text"]),
        axis=1,
    ).astype("Int64")

    # Replace any missing category with a safe placeholder (no crash).
    df["category"] = df["category"].fillna("Unknown")

    # Fixed-rate conversion: 1 GBP = 105.50 INR
    df["price_inr"] = (df["price_gbp"] * config.GBP_TO_INR).round(2)

    clean = df[["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]].copy()

    before = len(clean)
    clean = clean.dropna(subset=["title", "price_gbp", "rating", "in_stock", "category"])
    dropped = before - len(clean)
    if dropped:
        logger.warning("Dropped %d rows with missing essential fields", dropped)

    # Type the columns for clean downstream storage.
    clean["in_stock"] = clean["in_stock"].astype(int)
    clean["rating"] = clean["rating"].astype(int)
    clean["price_gbp"] = clean["price_gbp"].astype(float)
    clean["price_inr"] = clean["price_inr"].astype(float)

    clean = clean.reset_index(drop=True)
    logger.info("Cleaned books: %d rows ready", len(clean))
    return clean


def save_cleaned(df: pd.DataFrame, path=config.CLEANED_BOOKS_CSV) -> None:
    """Persist the cleaned DataFrame to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Saved %d cleaned records to %s", len(df), path)
