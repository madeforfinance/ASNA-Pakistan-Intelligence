import os
import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("INTELLIGENCE_DB", "data/intelligence.db")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "1551362175459663934"))

DIGEST_CHANNEL_NAME = "daily-intelligence"
HOURS_BACK = 24
MAX_EVENTS = 30

intents = discord.Intents.default()
intents.guilds = True
bot = discord.Client(intents=intents)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def clean(value, fallback="N/A"):
    if value is None:
        return fallback
    value = str(value).strip()
    return value or fallback


def trunc(value, limit):
    value = clean(value, "")
    return value if len(value) <= limit else value[:limit - 3].rstrip() + "..."


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def value(row, name, default=None):
    try:
        return row[name] if row[name] is not None else default
    except Exception:
        return default


def severity(score):
    score = safe_int(score)
    if score >= 80:
        return "BREAKING"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS digest_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            digest_date TEXT UNIQUE NOT NULL,
            digest_type TEXT NOT NULL DEFAULT 'daily',
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_count INTEGER DEFAULT 0
        )
    """)
    # Backward compatibility if the old table was created by an earlier version.
    cols = columns(conn, "digest_runs")
    if "digest_type" not in cols:
        conn.execute(
            "ALTER TABLE digest_runs ADD COLUMN digest_type TEXT NOT NULL DEFAULT 'daily'"
        )
    conn.commit()


def already_sent(conn, digest_type, date_key):
    row = conn.execute(
        "SELECT 1 FROM digest_runs WHERE digest_type=? AND digest_date=?",
        (digest_type, date_key),
    ).fetchone()
    return row is not None


def mark_sent(conn, digest_type, date_key, count):
    conn.execute(
        """
        INSERT OR IGNORE INTO digest_runs
        (digest_date, digest_type, event_count)
        VALUES (?, ?, ?)
        """,
        (date_key, digest_type, count),
    )
    conn.commit()


def fetch_events():
    conn = db()
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)
    ).strftime("%Y-%m-%d %H:%M:%S")

    event_cols = columns(conn, "events")
    analysis_cols = columns(conn, "analyses") if "analyses" in {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    } else set()

    # Select only analysis columns that are actually present.
    analysis_select = []
    for name in (
        "business_impact",
        "consumer_impact",
        "investor_impact",
        "government_impact",
        "overall_impact",
        "direction",
        "confidence",
        "importance_score",
    ):
        if name in analysis_cols:
            analysis_select.append(f"a.{name} AS analysis_{name}")

    select = """
        e.id AS event_id,
        e.headline,
        e.summary,
        e.category,
        e.subcategory,
        e.importance,
        e.confidence AS event_confidence,
        e.first_seen,
        e.last_updated
    """
    if analysis_select:
        select += ", " + ", ".join(analysis_select)

    query = f"""
        SELECT {select}
        FROM events e
        LEFT JOIN analyses a ON a.event_id = e.id
        WHERE e.first_seen >= ? OR e.last_updated >= ?
        ORDER BY e.last_updated DESC
    """

    rows = conn.execute(query, (cutoff, cutoff)).fetchall()
    conn.close()

    result = []
    seen = set()

    for row in rows:
        event_id = value(row, "event_id")
        if event_id in seen:
            continue
        seen.add(event_id)

        score = safe_int(
            value(row, "analysis_importance_score"),
            safe_int(value(row, "importance"), 1) * 20,
        )

        result.append({
            "id": event_id,
            "headline": clean(value(row, "headline"), "Untitled event"),
            "summary": clean(value(row, "summary"), "No summary available."),
            "category": clean(value(row, "category"), "general").lower(),
            "subcategory": clean(value(row, "subcategory"), ""),
            "score": score,
            "severity": severity(score),
            "confidence": clean(
                value(row, "analysis_confidence"),
                value(row, "event_confidence", "Unknown"),
            ),
            "direction": clean(value(row, "analysis_direction"), "Neutral"),
            "business": clean(value(row, "analysis_business_impact"), ""),
            "consumer": clean(value(row, "analysis_consumer_impact"), ""),
            "investor": clean(value(row, "analysis_investor_impact"), ""),
            "government": clean(value(row, "analysis_government_impact"), ""),
        })

    result.sort(key=lambda x: x["score"], reverse=True)
    return result[:MAX_EVENTS]


CATEGORY_NAMES = {
    "finance": "💰 Finance",
    "markets": "📈 Markets",
    "business": "🏢 Business",
    "economy": "🌐 Economy",
    "energy": "⚡ Energy",
    "trade": "🚢 Trade",
    "regulatory": "⚖️ Regulatory",
    "technology": "💻 Technology",
    "agriculture": "🌾 Agriculture",
    "banking": "🏦 Banking",
    "general": "📰 General",
}


def icon(level):
    return {
        "BREAKING": "🚨",
        "HIGH": "🔴",
        "MEDIUM": "🟠",
        "LOW": "🟢",
    }.get(level, "⚪")


def get_channel(guild):
    async def inner():
        for channel in guild.text_channels:
            if channel.name == DIGEST_CHANNEL_NAME:
                return channel

        category = next(
            (c for c in guild.categories if "intelligence" in c.name.lower()),
            None,
        )

        if category is None:
            category = await guild.create_category("🧠 INTELLIGENCE")

        return await guild.create_text_channel(
            DIGEST_CHANNEL_NAME,
            category=category,
            topic="ASNA Pakistan Intelligence Daily Digest",
        )

    return inner()


def executive_embed(events):
    today = datetime.now().strftime("%d %B %Y")
    breaking = sum(e["severity"] == "BREAKING" for e in events)
    high = sum(e["severity"] == "HIGH" for e in events)

    description = (
        f"**{len(events)} significant events** processed during the last "
        f"{HOURS_BACK} hours.\n"
        f"🚨 Breaking: **{breaking}** | 🔴 High: **{high}**"
    )

    if events:
        description += (
            f"\n\nMost significant: **{trunc(events[0]['headline'], 220)}**"
        )

    embed = discord.Embed(
        title=f"🧠 ASNA Pakistan Intelligence | {today}",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc),
    )

    lines = []
    for i, e in enumerate(events[:10], 1):
        lines.append(
            f"{i}. {icon(e['severity'])} "
            f"**{trunc(e['headline'], 170)}**"
        )

    if lines:
        embed.add_field(
            name="🔥 Top Developments",
            value=trunc("\n".join(lines), 4500),
            inline=False,
        )

    embed.set_footer(text="ASNA Pakistan Intelligence • Daily Digest")
    return embed


def category_embeds(events):
    groups = {}
    for event in events:
        groups.setdefault(event["category"], []).append(event)

    embeds = []
    order = [
        "finance", "markets", "business", "economy", "energy",
        "trade", "regulatory", "technology", "agriculture",
        "banking", "general",
    ]

    for category in order:
        items = groups.get(category, [])
        if not items:
            continue

        embed = discord.Embed(
            title=f"🧠 {CATEGORY_NAMES.get(category, category.title())}",
            color=discord.Color.dark_blue(),
        )

        for event in items[:5]:
            text = (
                f"{icon(event['severity'])} "
                f"**{trunc(event['headline'], 180)}**\n"
                f"{trunc(event['summary'], 420)}\n"
                f"Direction: **{event['direction']}** | "
                f"Importance: **{event['severity']}** | "
                f"Confidence: **{event['confidence']}**"
            )
            embed.add_field(
                name="\u200b",
                value=trunc(text, 950),
                inline=False,
            )

        embeds.append(embed)

    return embeds


def impact_embeds(events):
    important = [e for e in events if e["score"] >= 60]
    if not important:
        return []

    embeds = []
    current = None
    count = 0

    for event in important[:10]:
        if current is None:
            current = discord.Embed(
                title="🎯 Business & Economic Impact",
                color=discord.Color.orange(),
            )
            count = 0

        lines = [f"**{trunc(event['headline'], 170)}**"]

        if event["business"]:
            lines.append(f"🏢 Business: {trunc(event['business'], 220)}")
        if event["consumer"]:
            lines.append(f"👥 Consumer: {trunc(event['consumer'], 220)}")
        if event["investor"]:
            lines.append(f"📈 Investor: {trunc(event['investor'], 220)}")
        if event["government"]:
            lines.append(f"🏛️ Government: {trunc(event['government'], 220)}")

        current.add_field(
            name="\u200b",
            value=trunc("\n".join(lines), 950),
            inline=False,
        )
        count += 1

        if count == 5:
            embeds.append(current)
            current = None

    if current is not None:
        embeds.append(current)

    return embeds


@bot.event
async def on_ready():
    print("=" * 60)
    print("ASNA DAILY INTELLIGENCE DIGEST")
    print("=" * 60)

    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("[ERROR] Guild not found.")
        await bot.close()
        return

    conn = db()
    ensure_table(conn)

    date_key = datetime.now().strftime("%Y-%m-%d")
    if already_sent(conn, "daily", date_key):
        print("[DIGEST] Today's digest already sent.")
        conn.close()
        await bot.close()
        return
    conn.close()

    events = fetch_events()
    print(f"[DATABASE] Events selected: {len(events)}")

    channel = await get_channel(guild)

    try:
        await channel.send(embed=executive_embed(events))

        cats = category_embeds(events)
        for embed in cats:
            await channel.send(embed=embed)

        impacts = impact_embeds(events)
        for embed in impacts:
            await channel.send(embed=embed)

        conn = db()
        ensure_table(conn)
        mark_sent(conn, "daily", date_key, len(events))
        conn.close()

        print(f"[DISCORD] Digest sent to #{channel.name}")
        print(f"[DISCORD] Category embeds: {len(cats)}")
        print(f"[DISCORD] Impact embeds: {len(impacts)}")
        print("[SYSTEM] Daily digest complete.")

    except Exception as exc:
        print(f"[DISCORD ERROR] {exc}")

    await bot.close()


if __name__ == "__main__":
    if not TOKEN:
        print("[ERROR] DISCORD_TOKEN is missing from .env")
    else:
        bot.run(TOKEN)
