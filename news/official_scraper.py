"""
ASNA Pakistan Intelligence
Official Government / Regulatory Source Scraper

Scrapes official Pakistani government and regulatory websites
when RSS feeds are unavailable.

Sources:
- State Bank of Pakistan
- Federal Board of Revenue
- SECP
- Pakistan Stock Exchange
- Pakistan Bureau of Statistics
- NEPRA
- OGRA
- Ministry of Finance
- Ministry of Commerce
"""

import hashlib
import re
import sqlite3
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


DB_PATH = "data/intelligence.db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 25


# ============================================================
# OFFICIAL SOURCE CONFIGURATION
# ============================================================

SOURCES = [
    {
        "name": "State Bank of Pakistan",
        "url": "https://archive.sbp.org.pk/press/2026/index2.asp",
        "category": "finance",
        "subcategory": "monetary_policy",
    },

    {
        "name": "Federal Board of Revenue",
        "url": "https://www.fbr.gov.pk/pr",
        "category": "finance",
        "subcategory": "taxation",
    },

    {
        "name": "SECP",
        "url": "https://www.secp.gov.pk/media-center/press-releases/",
        "category": "business",
        "subcategory": "corporate_regulation",
    },

    {
        "name": "Pakistan Stock Exchange",
        "url": "https://www.psx.com.pk/psx/announcement/corporate-announcements",
        "category": "markets",
        "subcategory": "stock_exchange",
    },

    {
        "name": "Pakistan Bureau of Statistics",
        "url": "https://www.pbs.gov.pk/press-release/",
        "category": "economy",
        "subcategory": "economic_data",
    },

    {
        "name": "NEPRA",
        "url": "https://nepra.org.pk/news.php",
        "category": "energy",
        "subcategory": "electricity",
    },

    {
        "name": "OGRA",
        "url": "https://www.ogra.org.pk/index.php/press-releases-2",
        "category": "energy",
        "subcategory": "oil_gas",
    },

    {
        "name": "Ministry of Finance Pakistan",
        "url": "https://finance.gov.pk/press_releases.html",
        "category": "finance",
        "subcategory": "government_finance",
    },

    {
        "name": "Ministry of Commerce Pakistan",
        "url": "https://www.commerce.gov.pk/notifications/",
        "category": "trade",
        "subcategory": "commerce",
    },
]


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_hash(title, url):
    raw = f"{title}|{url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def valid_title(title):
    if not title:
        return False

    title = clean_text(title)

    if len(title) < 15:
        return False

    bad_titles = {
        "home",
        "contact us",
        "about us",
        "read more",
        "click here",
        "view",
        "login",
        "search",
        "menu",
    }

    return title.lower() not in bad_titles


def looks_like_article_link(url, title):
    """
    Generic filtering to prevent menus/navigation from becoming articles.
    """

    if not url:
        return False

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False

    if not valid_title(title):
        return False

    lower_url = url.lower()

    blocked = [
        "/login",
        "/contact",
        "/about",
        "/privacy",
        "/terms",
        "javascript:",
        "#",
    ]

    if any(x in lower_url for x in blocked):
        return False

    return True


def request_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    return response.text


# ============================================================
# DATABASE
# ============================================================

def get_source_id(conn, source_name):
    row = conn.execute(
        """
        SELECT id
        FROM sources
        WHERE name = ?
        LIMIT 1
        """,
        (source_name,),
    ).fetchone()

    return row[0] if row else None


def article_exists(conn, article_hash):
    row = conn.execute(
        """
        SELECT id
        FROM articles
        WHERE hash = ?
        LIMIT 1
        """,
        (article_hash,),
    ).fetchone()

    return row is not None


def save_article(conn, source, article):
    source_id = get_source_id(conn, source["name"])

    if source_id is None:
        print(
            f"[WARN] Source not found in database: "
            f"{source['name']}"
        )
        return False

    title = clean_text(article.get("title"))
    url = article.get("url")
    description = clean_text(article.get("description"))
    published_at = article.get("published_at")

    article_hash = make_hash(title, url)

    if article_exists(conn, article_hash):
        return False

    conn.execute(
        """
        INSERT INTO articles (
            source_id,
            title,
            url,
            description,
            content,
            published_at,
            category,
            subcategory,
            location,
            hash,
            processed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            source_id,
            title,
            url,
            description,
            description,
            published_at,
            source["category"],
            source["subcategory"],
            "Pakistan",
            article_hash,
        ),
    )

    return True


# ============================================================
# DATE EXTRACTION
# ============================================================

DATE_PATTERNS = [
    r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
    r"\b\d{1,2}[-/][A-Za-z]{3,9}[-/]\d{4}\b",
    r"\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\b",
    r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
]


def extract_date(text):
    if not text:
        return None

    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)

        if match:
            return match.group(0)

    return None


# ============================================================
# GENERIC LINK EXTRACTION
# ============================================================

def extract_links(soup, base_url, source_name):
    results = []
    seen = set()

    for link in soup.find_all("a", href=True):

        href = link.get("href")
        title = clean_text(link.get_text(" ", strip=True))

        if not href:
            continue

        absolute_url = urljoin(base_url, href)

        if absolute_url in seen:
            continue

        if not looks_like_article_link(absolute_url, title):
            continue

        seen.add(absolute_url)

        parent_text = ""

        parent = link.parent

        if parent:
            parent_text = clean_text(
                parent.get_text(" ", strip=True)
            )

        combined_text = f"{title} {parent_text}"

        published_at = extract_date(combined_text)

        results.append(
            {
                "title": title,
                "url": absolute_url,
                "description": parent_text,
                "published_at": published_at,
            }
        )

    return results


# ============================================================
# SOURCE-SPECIFIC FILTERS
# ============================================================

def filter_source_articles(source_name, articles):

    filtered = []

    source_name_lower = source_name.lower()

    for article in articles:

        title = article["title"].lower()
        url = article["url"].lower()

        # ----------------------------------------------------
        # FBR
        # ----------------------------------------------------

        if "federal board of revenue" in source_name_lower:

            if (
                "fbr" in url
                or "press" in url
                or "release" in url
                or "chairman" in title
                or "customs" in title
                or "tax" in title
            ):
                filtered.append(article)

        # ----------------------------------------------------
        # SECP
        # ----------------------------------------------------

        elif source_name == "SECP":

            if (
                "press" in url
                or "secp" in url
                or "corporate" in title
                or "companies" in title
                or "capital market" in title
                or "insurance" in title
                or "digital" in title
            ):
                filtered.append(article)

        # ----------------------------------------------------
        # PSX
        # ----------------------------------------------------

        elif source_name == "Pakistan Stock Exchange":

            if (
                "announcement" in url
                or "media-center" in url
                or "exchange" in title
                or "financial" in title
                or "listing" in title
                or "board meeting" in title
                or "material information" in title
            ):
                filtered.append(article)

        # ----------------------------------------------------
        # PBS
        # ----------------------------------------------------

        elif source_name == "Pakistan Bureau of Statistics":

            if (
                "press" in url
                or "cpi" in title
                or "inflation" in title
                or "national accounts" in title
                or "agriculture" in title
                or "statistics" in title
            ):
                filtered.append(article)

        # ----------------------------------------------------
        # NEPRA
        # ----------------------------------------------------

        elif source_name == "NEPRA":

            if (
                "nepra" in url
                or "notification" in title
                or "determination" in title
                or "tariff" in title
                or "hearing" in title
                or "decision" in title
                or "license" in title
                or "licence" in title
            ):
                filtered.append(article)

        # ----------------------------------------------------
        # OGRA
        # ----------------------------------------------------

        elif source_name == "OGRA":

            if (
                "press" in url
                or "lpg" in title
                or "rlng" in title
                or "petroleum" in title
                or "price" in title
                or "gas" in title
            ):
                filtered.append(article)

        # ----------------------------------------------------
        # MINISTRY OF FINANCE
        # ----------------------------------------------------

        elif source_name == "Ministry of Finance Pakistan":

            if (
                "press" in url
                or "finance" in title
                or "budget" in title
                or "fiscal" in title
                or "revenue" in title
                or "economic" in title
                or "debt" in title
            ):
                filtered.append(article)

        # ----------------------------------------------------
        # MINISTRY OF COMMERCE
        # ----------------------------------------------------

        elif source_name == "Ministry of Commerce Pakistan":

            if (
                "notification" in url
                or "commerce" in title
                or "trade" in title
                or "export" in title
                or "import" in title
                or "tariff" in title
                or "sro" in title
            ):
                filtered.append(article)

        # ----------------------------------------------------
        # SBP
        # ----------------------------------------------------

        elif source_name == "State Bank of Pakistan":

            if (
                "press" in url
                or "sbp" in url
                or "monetary" in title
                or "policy" in title
                or "bank" in title
                or "exchange" in title
                or "payment" in title
                or "foreign" in title
            ):
                filtered.append(article)

        else:
            filtered.append(article)

    return filtered


# ============================================================
# SCRAPE ONE SOURCE
# ============================================================

def scrape_source(source):

    print()
    print("=" * 70)
    print(f"[SOURCE] {source['name']}")
    print(f"[URL]    {source['url']}")
    print("=" * 70)

    try:
        html = request_page(source["url"])

        soup = BeautifulSoup(html, "lxml")

        articles = extract_links(
            soup,
            source["url"],
            source["name"],
        )

        articles = filter_source_articles(
            source["name"],
            articles,
        )

        # Remove duplicate URLs
        unique = {}
        for article in articles:
            unique[article["url"]] = article

        articles = list(unique.values())

        # Keep latest/first 40 candidates
        articles = articles[:40]

        print(
            f"[SUCCESS] {source['name']}: "
            f"{len(articles)} candidate articles"
        )

        return articles

    except requests.exceptions.HTTPError as e:

        status = getattr(
            e.response,
            "status_code",
            "unknown",
        )

        print(
            f"[ERROR] {source['name']}: "
            f"HTTP {status}"
        )

    except requests.exceptions.RequestException as e:

        print(
            f"[ERROR] {source['name']}: "
            f"Network error: {e}"
        )

    except Exception as e:

        print(
            f"[ERROR] {source['name']}: "
            f"{type(e).__name__}: {e}"
        )

    return []


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("ASNA OFFICIAL SOURCE SCRAPER")
    print("=" * 70)
    print()

    conn = sqlite3.connect(DB_PATH)

    total_sources = 0
    successful_sources = 0
    failed_sources = 0
    total_candidates = 0
    total_saved = 0

    for source in SOURCES:

        total_sources += 1

        articles = scrape_source(source)

        if not articles:
            failed_sources += 1
            continue

        successful_sources += 1

        total_candidates += len(articles)

        saved_for_source = 0

        for article in articles:

            try:

                if save_article(
                    conn,
                    source,
                    article,
                ):
                    saved_for_source += 1

            except Exception as e:

                print(
                    f"[WARN] Could not save article: "
                    f"{e}"
                )

        conn.commit()

        total_saved += saved_for_source

        print(
            f"[DATABASE] {source['name']}: "
            f"{saved_for_source} new articles saved"
        )

        time.sleep(1)

    conn.close()

    print()
    print("=" * 70)
    print("SCRAPER SUMMARY")
    print("=" * 70)

    print(f"Sources checked:       {total_sources}")
    print(f"Sources successful:    {successful_sources}")
    print(f"Sources failed:        {failed_sources}")
    print(f"Candidate articles:    {total_candidates}")
    print(f"New articles saved:    {total_saved}")

    print("=" * 70)
    print()


if __name__ == "__main__":
    main()