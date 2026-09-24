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
CHANNEL = "weekly-intelligence"
LOOKBACK_DAYS = 7

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
            topic="ASNA Pakistan Intelligence Weekly Report",
        )
    return inner()


def fetch():
    c = db()
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    ).strftime("%Y-%m-%d %H:%M:%S")

    rows = c.execute(
        """
        SELECT id, headline, summary, category, subcategory,
               importance, confidence, first_seen, last_updated
        FROM events
        WHERE first_seen >= ? OR last_updated >= ?
        ORDER BY importance DESC, last_updated DESC
        """,
        (cutoff, cutoff),
    ).fetchall()
    c.close()
    return rows


def build(rows):
    counts = Counter(clean(r["category"], "general").lower() for r in rows)
    high = [r for r in rows if int(r["importance"] or 0) >= 3]

    embed = discord.Embed(
        title=f"📊 ASNA Pakistan Weekly Intelligence | {datetime.now():%d %B %Y}",
        description=(
            f"Seven-day intelligence summary covering **{len(rows)} events**. "
            "Counts describe captured intelligence, not the total number of "
            "events occurring in Pakistan."
        ),
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc),
    )

    if counts:
        embed.add_field(
            name="Activity by Category",
            value="\n".join(
                f"• **{k.title()}**: {v}"
                for k, v in counts.most_common()
            )[:1000],
            inline=False,
        )

    if high:
        lines = []
        for i, r in enumerate(high[:10], 1):
            lines.append(
                f"{i}. **{trunc(r['headline'], 170)}** "
                f"`Importance {r['importance']}`"
            )
        embed.add_field(
            name="Major Developments",
            value="\n".join(lines)[:4000],
            inline=False,
        )

    embed.set_footer(text="ASNA Pakistan Intelligence • Weekly Report")
    return embed


@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("[ERROR] Guild not found.")
        await bot.close()
        return

    rows = fetch()
    channel = await channel_for(guild)

    try:
        await channel.send(embed=build(rows))
        print(f"[WEEKLY] Report sent. Events: {len(rows)}")
    except Exception as exc:
        print(f"[WEEKLY ERROR] {exc}")

    await bot.close()


if __name__ == "__main__":
    if not TOKEN:
        print("[ERROR] DISCORD_TOKEN is missing from .env")
    else:
        bot.run(TOKEN)
