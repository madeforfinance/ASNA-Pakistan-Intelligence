import os
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("INTELLIGENCE_DB", "data/intelligence.db")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "1551362175459663934"))
CHANNEL = "source-health"

intents = discord.Intents.default()
intents.guilds = True
bot = discord.Client(intents=intents)


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def check_url(url):
    if not url:
        return "NO_URL"

    try:
        req = Request(
            url,
            headers={"User-Agent": "ASNA-Pakistan-Intelligence/1.0"},
        )
        with urlopen(req, timeout=12) as response:
            return f"HTTP {response.status}"
    except HTTPError as e:
        return f"HTTP {e.code}"
    except URLError as e:
        return f"URL ERROR"
    except Exception:
        return "ERROR"


def get_channel(guild):
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
            topic="ASNA Pakistan Intelligence Source Health",
        )
    return inner()


@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        await bot.close()
        return

    c = db()
    sources = c.execute(
        """
        SELECT id, name, url, feed_url, active, priority
        FROM sources
        WHERE active=1
        ORDER BY priority ASC, name ASC
        """
    ).fetchall()

    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).strftime("%Y-%m-%d %H:%M:%S")

    lines = []

    for s in sources:
        feed_status = check_url(s["feed_url"]) if s["feed_url"] else "NO_FEED"

        recent = c.execute(
            """
            SELECT COUNT(*)
            FROM articles
            WHERE source_id=? AND fetched_at>=?
            """,
            (s["id"], cutoff),
        ).fetchone()[0]

        lines.append(
            f"**{s['name']}**\n"
            f"Feed: `{feed_status}` | Articles 24h: `{recent}`"
        )

    c.close()

    embed = discord.Embed(
        title="🔎 ASNA Source Health",
        description="\n\n".join(lines)[:5900] or "No active sources found.",
        color=discord.Color.teal(),
        timestamp=datetime.now(timezone.utc),
    )

    channel = await get_channel(guild)

    try:
        await channel.send(embed=embed)
        print(f"[SOURCE HEALTH] Checked {len(sources)} sources.")
    except Exception as exc:
        print(f"[SOURCE HEALTH ERROR] {exc}")

    await bot.close()


if __name__ == "__main__":
    if not TOKEN:
        print("[ERROR] DISCORD_TOKEN is missing from .env")
    else:
        bot.run(TOKEN)
