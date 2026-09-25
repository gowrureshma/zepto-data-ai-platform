"""SQL queries + execution.

At least 5 queries that collectively demonstrate:
SELECT, WHERE, ORDER BY, LIMIT, DISTINCT, IN (or BETWEEN), JOIN.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from . import config

logger = logging.getLogger(__name__)

# Each query is (label, sql). Queries are ordered to showcase the required
# SQL features: SELECT, DISTINCT, WHERE, ORDER BY, LIMIT, BETWEEN, IN, JOIN.
QUERIES: list[tuple[str, str]] = [
    (
        "Q1 - SELECT all categories (SELECT, ORDER BY)",
        """
        SELECT category_id, category_name
        FROM categories
        ORDER BY category_id;
        """,
    ),
    (
        "Q2 - DISTINCT star ratings present (DISTINCT, ORDER BY)",
        """
        SELECT DISTINCT rating
        FROM books
        ORDER BY rating;
        """,
    ),
    (
        "Q3 - WHERE: in-stock books priced above £30 (WHERE, ORDER BY)",
        """
        SELECT title, price_gbp, price_inr
        FROM books
        WHERE in_stock = 1 AND price_gbp > 30
        ORDER BY price_gbp DESC;
        """,
    ),
    (
        "Q4 - ORDER BY + LIMIT: top 5 most expensive books (ORDER BY, LIMIT)",
        """
        SELECT title, price_gbp, category_id
        FROM books
        ORDER BY price_gbp DESC
        LIMIT 5;
        """,
    ),
    (
        "Q5 - BETWEEN: books priced between £20 and £40 (BETWEEN, ORDER BY)",
        """
        SELECT title, price_gbp, rating
        FROM books
        WHERE price_gbp BETWEEN 20 AND 40
        ORDER BY price_gbp;
        """,
    ),
    (
        "Q6 - IN: books in selected categories (IN, subquery, ORDER BY)",
        """
        SELECT title, price_gbp, rating
        FROM books
        WHERE category_id IN (
            SELECT category_id FROM categories
            WHERE category_name IN ('Travel', 'Mystery', 'Poetry')
        )
        ORDER BY price_gbp DESC
        LIMIT 10;
        """,
    ),
    (
        "Q7 - JOIN: books with category names (JOIN, ORDER BY, LIMIT)",
        """
        SELECT b.book_id, b.title, b.price_gbp, b.price_inr, b.rating,
               b.in_stock, c.category_name
        FROM books b
        JOIN categories c ON b.category_id = c.category_id
        ORDER BY b.price_gbp DESC
        LIMIT 15;
        """,
    ),
]


def _format_table(rows: list[dict[str, Any]]) -> str:
    """Render a list of row dicts as a simple fixed-width text table."""
    if not rows:
        return "(no rows)"
    headers = list(rows[0].keys())
    widths = {h: len(str(h)) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(row.get(h))))
    sep = "  ".join("-" * widths[h] for h in headers)
    header_line = "  ".join(str(h).ljust(widths[h]) for h in headers)
    lines = [header_line, sep]
    for row in rows:
        lines.append("  ".join(str(row.get(h)).ljust(widths[h]) for h in headers))
    return "\n".join(lines)


def run_queries(db_path=config.DB_PATH, out_path=config.SQL_OUTPUTS_PATH) -> dict[str, Any]:
    """Execute every query, print results, and save them to a text file."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    results: dict[str, Any] = {}

    blocks: list[str] = []
    for label, sql in QUERIES:
        try:
            cur = conn.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]
        except sqlite3.Error as exc:
            logger.error("%s failed: %s", label, exc)
            rows = []
            results[label] = {"sql": sql, "rows": [], "count": 0, "error": str(exc)}
            blocks.append(f"{'=' * 70}\n{label}\n{'=' * 70}\nSQL:\n{sql}\nError: {exc}\n")
            continue

        results[label] = {"sql": sql, "rows": rows, "count": len(rows)}
        block = [
            "=" * 70,
            label,
            "=" * 70,
            "SQL:",
            sql,
            f"Rows returned: {len(rows)}",
            "Output:",
            _format_table(rows),
            "",
        ]
        blocks.append("\n".join(block))

    conn.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(blocks), encoding="utf-8")
    logger.info("Saved SQL query outputs to %s", out_path)
    return results


def print_query_summary(results: dict[str, Any]) -> None:
    """Print a short per-query row count summary to the log."""
    for label, payload in results.items():
        count = payload.get("count", "-")
        logger.info("[%-45s] rows=%s", label.split(" - ")[0], count)
