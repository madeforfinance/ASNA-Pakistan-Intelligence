import os
import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("INTELLIGENCE_DB", "data/intelligence.db")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "1551362175459663934"))
CHANNEL = "system-health"

intents = discord.Intents.default()
intents.guilds = True
bot = discord.Client(intents=intents)


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def table_exists(c, name):
    return c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def count(c, table):
    if not table_exists(c, table):
        return 0
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def channel_for(guild):
    async def inner():
        for ch in guild.text_channels:
            if ch.name == CHANNEL:
                return ch
        category = next(
            (c for c in guild.categories if "system" in c.name.lower()),
            None,
        )
        if category is None:
            category = await guild.create_category("⚙️ SYSTEM")
        return await guild.create_text_channel(
            CHANNEL,
            category=category,
            topic="ASNA Pakistan Intelligence System Health",
        )
    return inner()


@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("[HEALTH] Guild not found.")
        await bot.close()
        return

    c = db()

    tables = [
        "sources",
        "articles",
        "events",
        "analyses",
        "alerts",
    ]

    lines = []
    for table in tables:
        status = "ONLINE" if table_exists(c, table) else "MISSING"
        lines.append(f"**{table}**: `{status}` | Records: `{count(c, table)}`")

    # Recent article/event activity
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).strftime("%Y-%m-%d %H:%M:%S")

    recent_articles = 0
    recent_events = 0

    if table_exists(c, "articles"):
        recent_articles = c.execute(
            "SELECT COUNT(*) FROM articles WHERE fetched_at >= ?",
            (cutoff,),
        ).fetchone()[0]

    if table_exists(c, "events"):
        recent_events = c.execute(
            "SELECT COUNT(*) FROM events WHERE first_seen >= ? OR last_updated >= ?",
            (cutoff, cutoff),
        ).fetchone()[0]

    lines.append("")
    lines.append(f"📰 Articles in last 24h: **{recent_articles}**")
    lines.append(f"🧠 Events in last 24h: **{recent_events}**")

    embed = discord.Embed(
        title="⚙️ ASNA Intelligence System Health",
        description="\n".join(lines),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )

    c.close()

    channel = await channel_for(guild)

    try:
        await channel.send(embed=embed)
        print("[HEALTH] Health report sent.")
    except Exception as exc:
        print(f"[HEALTH ERROR] {exc}")

    await bot.close()


if __name__ == "__main__":
    if not TOKEN:
        print("[ERROR] DISCORD_TOKEN is missing from .env")
    else:
        bot.run(TOKEN)
