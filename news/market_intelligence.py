import os
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("INTELLIGENCE_DB", "data/intelligence.db")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "1551362175459663934"))
CHANNEL = "market-intelligence"
LOOKBACK_HOURS = 24

intents = discord.Intents.default()
intents.guilds = True
bot = discord.Client(intents=intents)


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def clean(v, default="N/A"):
    if v is None:
        return default
    v = str(v).strip()
    return v or default


def trunc(v, n):
    v = clean(v, "")
    return v if len(v) <= n else v[:n-3] + "..."


def ensure_table(c):
    c.execute("""
        CREATE TABLE IF NOT EXISTS market_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT UNIQUE NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_count INTEGER DEFAULT 0
        )
    """)
    c.commit()


def channel_for(guild):
    async def inner():
        for ch in guild.text_channels:
            if ch.name == CHANNEL:
                return ch

        category = next(
            (c for c in guild.categories if "intelligence" in c.name.lower()),
            None,
        )
        if category is None:
            category = await guild.create_category("🧠 INTELLIGENCE")

        return await guild.create_text_channel(
            CHANNEL,
            category=category,
            topic="ASNA Pakistan Market Intelligence",
        )
    return inner()


def fetch():
    c = db()
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    ).strftime("%Y-%m-%d %H:%M:%S")

    rows = c.execute(
        """
        SELECT id, headline, summary, category, subcategory,
               importance, confidence, first_seen, last_updated
        FROM events
        WHERE (first_seen >= ? OR last_updated >= ?)
          AND lower(coalesce(category, '')) IN
              ('markets','finance','banking','business','economy')
        ORDER BY importance DESC, last_updated DESC
        """,
        (cutoff, cutoff),
    ).fetchall()

    c.close()
    return rows


def build(rows):
    groups = Counter(clean(r["category"], "general").lower() for r in rows)

    embed = discord.Embed(
        title=f"📈 ASNA Market Intelligence | {datetime.now():%d %B %Y}",
        description=(
            "This report summarizes market-relevant events captured by "
            "the intelligence pipeline. It is event intelligence, not a "
            "live PSX price feed."
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )

    if groups:
        embed.add_field(
            name="Market Signal Distribution",
            value=" | ".join(
                f"**{k.title()}**: {v}" for k, v in groups.most_common()
            )[:1000],
            inline=False,
        )

    for row in rows[:8]:
        embed.add_field(
            name="\u200b",
            value=(
                f"**{trunc(row['headline'], 180)}**\n"
                f"{trunc(row['summary'], 420)}\n"
                f"Category: `{clean(row['category'])}` | "
                f"Importance: `{row['importance']}` | "
                f"Confidence: `{clean(row['confidence'])}`"
            )[:1000],
            inline=False,
        )

    if not rows:
        embed.add_field(
            name="No market events",
            value="No market-relevant events were captured in the last 24 hours.",
            inline=False,
        )

    embed.set_footer(text="ASNA Pakistan Intelligence • Market Intelligence")
    return embed


@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("[ERROR] Guild not found.")
        await bot.close()
        return

    c = db()
    ensure_table(c)

    date_key = datetime.now().strftime("%Y-%m-%d")
    if c.execute(
        "SELECT 1 FROM market_reports WHERE report_date=?",
        (date_key,),
    ).fetchone():
        print("[MARKET] Today's report already sent.")
        c.close()
        await bot.close()
        return

    rows = fetch()
    channel = await channel_for(guild)

    try:
        await channel.send(embed=build(rows))
        c.execute(
            "INSERT OR IGNORE INTO market_reports(report_date,event_count) VALUES(?,?)",
            (date_key, len(rows)),
        )
        c.commit()
        print(f"[MARKET] Report sent. Events: {len(rows)}")
    except Exception as exc:
        print(f"[MARKET ERROR] {exc}")

    c.close()
    await bot.close()


if __name__ == "__main__":
    if not TOKEN:
        print("[ERROR] DISCORD_TOKEN is missing from .env")
    else:
        bot.run(TOKEN)
