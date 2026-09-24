import aiosqlite
from pathlib import Path


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

DATABASE_PATH = DATA_DIR / "intelligence.db"


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

async def initialize_database():

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT,
                feed_url TEXT,
                source_type TEXT,
                category TEXT,
                priority INTEGER DEFAULT 3,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                title TEXT NOT NULL,
                url TEXT UNIQUE,
                description TEXT,
                content TEXT,
                published_at TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category TEXT,
                subcategory TEXT,
                location TEXT,
                hash TEXT UNIQUE,
                processed INTEGER DEFAULT 0,
                FOREIGN KEY(source_id)
                    REFERENCES sources(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_hash TEXT UNIQUE,
                headline TEXT NOT NULL,
                summary TEXT,
                category TEXT,
                subcategory TEXT,
                importance INTEGER DEFAULT 1,
                confidence TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_sources (
                event_id INTEGER,
                article_id INTEGER,
                PRIMARY KEY(event_id, article_id),
                FOREIGN KEY(event_id)
                    REFERENCES events(id),
                FOREIGN KEY(article_id)
                    REFERENCES articles(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER UNIQUE,

                what_happened TEXT,
                why_it_matters TEXT,

                business_impact TEXT,
                economic_impact TEXT,
                consumer_impact TEXT,
                investor_impact TEXT,
                government_impact TEXT,

                immediate_impact TEXT,
                short_term_impact TEXT,
                medium_term_impact TEXT,
                long_term_impact TEXT,

                affected_sectors TEXT,
                risks TEXT,
                opportunities TEXT,
                uncertainties TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(event_id)
                    REFERENCES events(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                asset_type TEXT,
                price REAL,
                change_percent REAL,
                currency TEXT,
                source TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                alert_type TEXT,
                channel_id TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(event_id)
                    REFERENCES events(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT,
                title TEXT,
                content TEXT,
                channel_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                schedule_type TEXT,
                schedule_value TEXT,
                active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        await db.commit()


# ============================================================
# DATABASE STATUS
# ============================================================

async def database_exists():

    return DATABASE_PATH.exists()


# ============================================================
# DATABASE STATISTICS
# ============================================================

async def get_database_stats():

    if not DATABASE_PATH.exists():

        return None

    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        tables = [
            "sources",
            "articles",
            "events",
            "analysis",
            "market_data",
            "alerts",
            "reports",
        ]

        stats = {}

        for table in tables:

            cursor = await db.execute(
                f"SELECT COUNT(*) FROM {table}"
            )

            result = await cursor.fetchone()

            stats[table] = result[0]

        return stats