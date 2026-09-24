import asyncio
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import aiohttp
import aiosqlite
import feedparser

from news.sources import PAKISTAN_SOURCES


# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_PATH = "data/intelligence.db"

REQUEST_TIMEOUT = 25
MAX_ARTICLES_PER_SOURCE = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36 "
    "ASNA-Pakistan-Intelligence/1.0"
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    """Clean HTML-ish text and excessive whitespace."""

    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_url(url):
    """Normalize article URL for duplicate detection."""

    if not url:
        return ""

    try:
        parts = urlsplit(url.strip())

        # Remove fragments
        normalized = urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                parts.query,
                "",
            )
        )

        return normalized

    except Exception:
        return url.strip()


def create_hash(title, url):
    """Create stable article hash."""

    normalized_title = clean_text(title).lower()
    normalized_url = normalize_url(url).lower()

    raw = f"{normalized_title}|{normalized_url}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def parse_published_date(entry):
    """Extract publication date from RSS entry."""

    # feedparser normalized timestamp
    if getattr(entry, "published_parsed", None):

        try:
            dt = datetime(
                *entry.published_parsed[:6],
                tzinfo=timezone.utc,
            )

            return dt.strftime("%Y-%m-%d %H:%M:%S")

        except Exception:
            pass

    if getattr(entry, "updated_parsed", None):

        try:
            dt = datetime(
                *entry.updated_parsed[:6],
                tzinfo=timezone.utc,
            )

            return dt.strftime("%Y-%m-%d %H:%M:%S")

        except Exception:
            pass

    # Fallback
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def extract_content(entry):
    """Extract available RSS content."""

    # RSS content blocks
    if hasattr(entry, "content"):

        try:

            parts = []

            for item in entry.content:

                value = item.get("value")

                if value:
                    parts.append(clean_text(value))

            if parts:
                return " ".join(parts)

        except Exception:
            pass

    # Summary fallback
    summary = getattr(entry, "summary", "")

    return clean_text(summary)


def classify_category(source):
    """Use source registry category."""

    category = source.get("category")

    if category:
        return category

    return "general"


# ============================================================
# DATABASE
# ============================================================

async def get_source_id(db, source_name):

    cursor = await db.execute(
        """
        SELECT id
        FROM sources
        WHERE name = ?
        LIMIT 1
        """,
        (source_name,),
    )

    row = await cursor.fetchone()

    return row[0] if row else None


async def sync_source_registry():

    print("\n[SYSTEM] Synchronizing source registry...")

    async with aiosqlite.connect(DATABASE_PATH) as db:

        for source in PAKISTAN_SOURCES:

            name = source["name"]

            # Check existing source
            cursor = await db.execute(
                """
                SELECT id
                FROM sources
                WHERE name = ?
                LIMIT 1
                """,
                (name,),
            )

            row = await cursor.fetchone()

            if row:

                # UPDATE existing record
                await db.execute(
                    """
                    UPDATE sources
                    SET
                        url = ?,
                        feed_url = ?,
                        source_type = ?,
                        category = ?,
                        priority = ?,
                        active = 1
                    WHERE id = ?
                    """,
                    (
                        source.get("url"),
                        source.get("feed_url"),
                        source.get("source_type"),
                        source.get("category"),
                        source.get("priority", 3),
                        row[0],
                    ),
                )

            else:

                # INSERT new source
                await db.execute(
                    """
                    INSERT INTO sources
                    (
                        name,
                        url,
                        feed_url,
                        source_type,
                        category,
                        priority,
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        source.get("name"),
                        source.get("url"),
                        source.get("feed_url"),
                        source.get("source_type"),
                        source.get("category"),
                        source.get("priority", 3),
                    ),
                )

        await db.commit()

    print("[SYSTEM] Source registry synchronized.")


# ============================================================
# FETCH RSS
# ============================================================

async def fetch_feed(session, source):

    name = source["name"]
    feed_url = source.get("feed_url")

    if not feed_url:

        return {
            "source": name,
            "success": False,
            "articles": [],
            "error": "No feed URL configured",
        }

    try:

        timeout = aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT
        )

        async with session.get(
            feed_url,
            timeout=timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": (
                    "application/rss+xml,"
                    "application/atom+xml,"
                    "application/xml,"
                    "text/xml,"
                    "text/html"
                ),
            },
            allow_redirects=True,
        ) as response:

            if response.status != 200:

                return {
                    "source": name,
                    "success": False,
                    "articles": [],
                    "error": f"HTTP {response.status}",
                }

            content = await response.read()

            parsed = feedparser.parse(content)

            articles = []

            for entry in parsed.entries[
                :MAX_ARTICLES_PER_SOURCE
            ]:

                title = clean_text(
                    getattr(entry, "title", "")
                )

                url = normalize_url(
                    getattr(entry, "link", "")
                )

                if not title or not url:
                    continue

                description = clean_text(
                    getattr(entry, "summary", "")
                )

                content_text = extract_content(entry)

                published_at = parse_published_date(
                    entry
                )

                article_hash = create_hash(
                    title,
                    url,
                )

                articles.append(
                    {
                        "source": name,
                        "title": title,
                        "url": url,
                        "description": description,
                        "content": content_text,
                        "published_at": published_at,
                        "category": classify_category(source),
                        "subcategory": "",
                        "location": "Pakistan",
                        "hash": article_hash,
                    }
                )

            return {
                "source": name,
                "success": True,
                "articles": articles,
                "error": None,
            }

    except asyncio.TimeoutError:

        return {
            "source": name,
            "success": False,
            "articles": [],
            "error": "Request timeout",
        }

    except Exception as e:

        return {
            "source": name,
            "success": False,
            "articles": [],
            "error": str(e),
        }


# ============================================================
# SAVE ARTICLES
# ============================================================

async def save_article(db, article):

    source_id = await get_source_id(
        db,
        article["source"],
    )

    if source_id is None:

        print(
            f"Could not save article: "
            f"source not found: {article['source']}"
        )

        return False

    # Check duplicate by hash
    cursor = await db.execute(
        """
        SELECT id
        FROM articles
        WHERE hash = ?
        LIMIT 1
        """,
        (article["hash"],),
    )

    existing = await cursor.fetchone()

    if existing:
        return False

    # Check duplicate by URL as secondary protection
    cursor = await db.execute(
        """
        SELECT id
        FROM articles
        WHERE url = ?
        LIMIT 1
        """,
        (article["url"],),
    )

    existing = await cursor.fetchone()

    if existing:
        return False

    # Correct schema
    await db.execute(
        """
        INSERT INTO articles
        (
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
            article["title"],
            article["url"],
            article["description"],
            article["content"],
            article["published_at"],
            article["category"],
            article["subcategory"],
            article["location"],
            article["hash"],
        ),
    )

    return True


# ============================================================
# COLLECT ALL SOURCES
# ============================================================

async def collect_all():

    print()
    print("=" * 70)
    print("ASNA PAKISTAN NEWS COLLECTOR")
    print("=" * 70)

    # First synchronize DB source records
    await sync_source_registry()

    connector = aiohttp.TCPConnector(
        limit=10,
        limit_per_host=2,
    )

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT
    )

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={
            "User-Agent": USER_AGENT
        },
    ) as session:

        tasks = [
            fetch_feed(session, source)
            for source in PAKISTAN_SOURCES
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

    # Statistics
    sources_checked = len(PAKISTAN_SOURCES)
    sources_successful = 0
    sources_failed = 0

    all_articles = []

    for result in results:

        if isinstance(result, Exception):

            sources_failed += 1

            print(
                f"Source failed: {result}"
            )

            continue

        if result["success"]:

            sources_successful += 1

            count = len(result["articles"])

            print(
                f"{result['source']}: "
                f"{count} articles"
            )

            all_articles.extend(
                result["articles"]
            )

        else:

            sources_failed += 1

            print(
                f"{result['source']} failed: "
                f"{result['error']}"
            )

    # Deduplicate in memory
    unique_articles = {}

    for article in all_articles:

        unique_articles[
            article["hash"]
        ] = article

    unique_list = list(
        unique_articles.values()
    )

    # Save to database
    new_articles = 0

    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        for article in unique_list:

            try:

                saved = await save_article(
                    db,
                    article,
                )

                if saved:
                    new_articles += 1

            except Exception as e:

                print(
                    "Could not save article: "
                    f"{e}"
                )

        await db.commit()

    # Final report
    print()
    print("=" * 70)

    print(
        f"Sources checked:      {sources_checked}"
    )

    print(
        f"Sources successful:   {sources_successful}"
    )

    print(
        f"Sources failed:       {sources_failed}"
    )

    print(
        f"Articles fetched:     {len(all_articles)}"
    )

    print(
        f"Unique articles:      {len(unique_list)}"
    )

    print(
        f"New articles saved:   {new_articles}"
    )

    print("=" * 70)

    return {
        "sources_checked": sources_checked,
        "sources_successful": sources_successful,
        "sources_failed": sources_failed,
        "articles_fetched": len(all_articles),
        "unique_articles": len(unique_list),
        "new_articles": new_articles,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        collect_all()
    )