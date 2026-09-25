"""Scraper for https://books.toscrape.com/.

Responsibilities:
    * Scrape the first ``NUM_PAGES`` pages of the All Products catalogue.
    * For every book collect: title, price, star_rating, availability, category.
    * Category is not on the listing page, so the book's detail page is fetched
      and the category is read from its breadcrumb (Home / Books / <category>).
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

logger = logging.getLogger(__name__)


def build_session() -> requests.Session:
    """Return a requests.Session with retries and a descriptive User-Agent."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": "zepto-data-ai-pipeline/1.0 (https://github.com/zepto-data-ai-platform)",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def _star_rating(article: BeautifulSoup) -> str:
    """Return the rating word (One..Five) from a product_pod article."""
    star = article.find("p", class_="star-rating")
    if not star:
        return ""
    for cls in star.get("class", []):
        if cls != "star-rating":
            return cls
    return ""


def _availability(article: BeautifulSoup) -> tuple[str, str]:
    """Return (availability_class, availability_text) from a product_pod."""
    avail = article.find("p", class_="availability")
    if not avail:
        return ("", "")
    classes = avail.get("class", [])
    av_class = "instock" if "instock" in classes else (
        "outofstock" if "outofstock" in classes else ""
    )
    text = avail.get_text(strip=True)
    return (av_class, text)


def _parse_book_from_article(article: BeautifulSoup, page_url: str) -> Optional[dict]:
    """Extract a raw book dict from a single product_pod <article>."""
    try:
        h3 = article.find("h3")
        if not h3:
            return None
        link = h3.find("a")
        if not link:
            return None

        # The <a title="..."> holds the full title; the link text is truncated.
        title = (link.get("title") or "").strip() or link.get_text(strip=True)

        href = link.get("href")
        if not href:
            return None
        detail_url = urljoin(page_url, href)

        price_el = article.find("p", class_="price_color")
        price_str = price_el.get_text(strip=True) if price_el else ""

        av_class, av_text = _availability(article)

        return {
            "title": title,
            "price_str": price_str,
            "star_rating": _star_rating(article),
            "availability_class": av_class,
            "availability_text": av_text,
            "detail_url": detail_url,
            "category": None,
        }
    except Exception as exc:  # never let one bad article kill the scrape
        logger.warning("Failed to parse article on %s: %s", page_url, exc)
        return None


def _fetch_category(session: requests.Session, detail_url: str) -> Optional[str]:
    """Fetch a book detail page and return its category from the breadcrumb."""
    try:
        resp = session.get(detail_url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        breadcrumb = soup.find("ul", class_="breadcrumb")
        if not breadcrumb:
            return None
        anchors = breadcrumb.find_all("a")
        # Breadcrumb layout: Home > Books > <category> [> <title>]
        if len(anchors) >= 3:
            return anchors[-1].get_text(strip=True)
        if len(anchors) == 2:
            active = breadcrumb.find("li", class_="active")
            return active.get_text(strip=True) if active else None
        return None
    except Exception as exc:
        logger.warning("Failed to fetch category from %s: %s", detail_url, exc)
        return None


def _enrich_categories(session: requests.Session, books: list[dict]) -> None:
    """Attach ``category`` to each book by fetching its detail page."""
    if not books:
        return

    def work(book: dict) -> None:
        book["category"] = _fetch_category(session, book["detail_url"])

    with ThreadPoolExecutor(max_workers=config.MAX_DETAIL_WORKERS) as pool:
        list(pool.map(work, books))

    missing = sum(1 for b in books if not b.get("category"))
    if missing:
        logger.warning("%d books had an unresolvable category", missing)


def scrape_listing_page(session: requests.Session, page_url: str) -> list[dict]:
    """Scrape one catalogue page and return the list of raw book dicts."""
    books: list[dict] = []
    try:
        resp = session.get(page_url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch listing page %s: %s", page_url, exc)
        return books

    # Pass resp.content (bytes) so BeautifulSoup sniffs the real encoding from
    # the HTML meta tag, avoiding ISO-8859-1 mojibake on the pound sign.
    soup = BeautifulSoup(resp.content, "html.parser")
    for article in soup.find_all("article", class_="product_pod"):
        book = _parse_book_from_article(article, page_url)
        if book:
            books.append(book)
    logger.info("Scraped %d books from %s", len(books), page_url)
    return books


def scrape_catalogue(pages: int = config.NUM_PAGES) -> list[dict]:
    """Scrape ``pages`` catalogue pages and enrich with categories."""
    session = build_session()
    try:
        books: list[dict] = []
        for page in range(1, pages + 1):
            url = config.CATALOGUE_PAGE_URL.format(page=page)
            books.extend(scrape_listing_page(session, url))
        logger.info("Total books scraped from listings: %d", len(books))
        _enrich_categories(session, books)
        return books
    finally:
        session.close()


def save_raw(books: list[dict], path=config.RAW_BOOKS_PATH) -> None:
    """Persist the raw scraped books to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(books, fh, ensure_ascii=False, indent=2)
    logger.info("Saved %d raw records to %s", len(books), path)
