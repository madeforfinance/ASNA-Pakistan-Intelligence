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
CHANNEL = "trend-intelligence"

intents = discord.Intents.default()
intents.guilds = True
bot = discord.Client(intents=intents)


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def get_channel(guild):
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
            topic="ASNA Pakistan Intelligence Trend Detection",
        )
    return inner()


@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        await bot.close()
        return

    now = datetime.now(timezone.utc)
    recent_cutoff = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    previous_cutoff = (now - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")

    c = db()

    recent = c.execute(
        """
        SELECT category, subcategory, headline
        FROM events
        WHERE first_seen >= ?
        """,
        (recent_cutoff,),
    ).fetchall()

    previous = c.execute(
        """
        SELECT category, subcategory
        FROM events
        WHERE first_seen >= ? AND first_seen < ?
        """,
        (previous_cutoff, recent_cutoff),
    ).fetchall()

    c.close()

    recent_categories = Counter(
        (r["category"] or "general").lower() for r in recent
    )
    previous_categories = Counter(
        (r["category"] or "general").lower() for r in previous
    )

    lines = []

    for category, count in recent_categories.most_common():
        baseline = previous_categories.get(category, 0)
        lines.append(
            f"**{category.title()}**: `{count}` events today "
            f"(7-day prior window: `{baseline}`)"
        )

    embed = discord.Embed(
        title="📡 ASNA Trend Intelligence",
        description=(
            "Rule-based trend detection using event frequency. "
            "This is a monitoring signal, not a prediction."
        ),
        color=discord.Color.gold(),
        timestamp=now,
    )

    embed.add_field(
        name="Category Activity",
        value="\n".join(lines)[:4500] or "No recent events.",
        inline=False,
    )

    channel = await get_channel(guild)

    try:
        await channel.send(embed=embed)
        print("[TREND] Trend report sent.")
    except Exception as exc:
        print(f"[TREND ERROR] {exc}")

    await bot.close()


if __name__ == "__main__":
    if not TOKEN:
        print("[ERROR] DISCORD_TOKEN is missing from .env")
    else:
        bot.run(TOKEN)
