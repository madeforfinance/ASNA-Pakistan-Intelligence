import os
import sqlite3
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

DATABASE_PATH = "data/intelligence.db"

GUILD_ID = 1551362175459663934

# Keep this at 10 during testing.
# Increase later after the routing system is verified.
MAX_ALERTS_PER_RUN = 10


# ============================================================
# SEVERITY COLORS
# ============================================================

SEVERITY_COLORS = {

    "BREAKING":
        discord.Color.red(),

    "HIGH":
        discord.Color.orange(),

    "MEDIUM":
        discord.Color.gold(),

    "LOW":
        discord.Color.green(),

}


# ============================================================
# SEVERITY CHANNELS
# ============================================================

SEVERITY_CHANNELS = {

    "BREAKING":
        "breaking-news",

    "HIGH":
        "high-impact",

    "MEDIUM":
        "important-updates",

    "LOW":
        "news-updates",

}


# ============================================================
# INTELLIGENCE CHANNELS
# ============================================================

INTELLIGENCE_CHANNELS = {

    "finance":
        "finance-intelligence",

    "markets":
        "market-intelligence",

    "business":
        "business-intelligence",

    "economy":
        "economy-intelligence",

    "energy":
        "energy-intelligence",

    "trade":
        "trade-intelligence",

    "regulatory":
        "regulatory-intelligence",

    "technology":
        "technology-intelligence",

    "agriculture":
        "agriculture-intelligence",

    "banking":
        "banking-intelligence",

    "general":
        "news-intelligence",

}


# ============================================================
# EVENT TYPE → INTELLIGENCE CHANNEL
# ============================================================

EVENT_CHANNEL_MAP = {

    # Finance
    "monetary_policy":
        "finance",

    "banking":
        "finance",

    # Markets
    "market_movement":
        "markets",

    "corporate_action":
        "markets",

    # Business
    "investment":
        "business",

    # Economy
    "inflation":
        "economy",

    "fiscal_policy":
        "economy",

    "imf":
        "economy",

    # Energy
    "energy":
        "energy",

    # Trade
    "trade":
        "trade",

    # Regulatory
    "tax_policy":
        "regulatory",

    "government_decision":
        "regulatory",

    # Default
    "general":
        "general",

}


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()

intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
)


# ============================================================
# DATABASE
# ============================================================

def get_database_connection():

    db = sqlite3.connect(
        DATABASE_PATH
    )

    db.row_factory = sqlite3.Row

    return db


# ============================================================
# DATABASE VERIFICATION
# ============================================================

def verify_database():

    db = get_database_connection()

    try:

        tables = {
            row[0]
            for row in db.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                """
            ).fetchall()
        }

        required_tables = [
            "events",
            "analyses",
            "alerts",
        ]

        missing_tables = [
            table
            for table in required_tables
            if table not in tables
        ]

        if missing_tables:

            print(
                "[ERROR] Missing database tables:"
            )

            for table in sorted(
                missing_tables
            ):

                print(
                    f"  - {table}"
                )

            return False

        # ----------------------------------------------------
        # EVENTS
        # ----------------------------------------------------

        event_columns = {
            row[1]
            for row in db.execute(
                "PRAGMA table_info(events)"
            ).fetchall()
        }

        required_event_columns = {

            "id",
            "event_hash",
            "headline",
            "summary",
            "category",
            "subcategory",
            "importance",
            "confidence",
            "first_seen",
            "last_updated",
            "status",

        }

        missing_event_columns = (
            required_event_columns
            - event_columns
        )

        if missing_event_columns:

            print(
                "[ERROR] Events table is missing:"
            )

            for column in sorted(
                missing_event_columns
            ):

                print(
                    f"  - {column}"
                )

            return False

        # ----------------------------------------------------
        # ALERTS
        # ----------------------------------------------------

        alert_columns = {
            row[1]
            for row in db.execute(
                "PRAGMA table_info(alerts)"
            ).fetchall()
        }

        required_alert_columns = {

            "id",
            "event_id",
            "alert_type",
            "channel_id",
            "sent_at",
            "severity",
            "score",
            "headline",
            "reason",
            "category",
            "direction",
            "status",

        }

        missing_alert_columns = (
            required_alert_columns
            - alert_columns
        )

        if missing_alert_columns:

            print(
                "[ERROR] Alerts table is missing:"
            )

            for column in sorted(
                missing_alert_columns
            ):

                print(
                    f"  - {column}"
                )

            return False

        print(
            "[SYSTEM] Database schema verified."
        )

        return True

    finally:

        db.close()


# ============================================================
# GUILD
# ============================================================

def get_guild():

    return bot.get_guild(
        GUILD_ID
    )


# ============================================================
# CHANNEL NAME NORMALIZATION
# ============================================================

def normalize_channel_name(name):

    return (
        name
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )


# ============================================================
# FIND CATEGORY
# ============================================================

def find_category(
    guild,
    keyword
):

    normalized_keyword = (
        normalize_channel_name(
            keyword
        )
    )

    for category in guild.categories:

        category_name = (
            normalize_channel_name(
                category.name
            )
        )

        if normalized_keyword in category_name:

            return category

    return None


# ============================================================
# GET OR CREATE INTELLIGENCE CATEGORY
# ============================================================

async def get_intelligence_category(
    guild
):

    category = find_category(
        guild,
        "intelligence"
    )

    if category:

        return category

    category = (
        await guild.create_category(
            "🧠 INTELLIGENCE"
        )
    )

    print(
        "[DISCORD] Created category: "
        "🧠 INTELLIGENCE"
    )

    return category


# ============================================================
# GET OR CREATE ALERT CATEGORY
# ============================================================

async def get_alert_category(
    guild
):

    category = find_category(
        guild,
        "alert"
    )

    if category:

        return category

    category = (
        await guild.create_category(
            "🚨 ALERTS"
        )
    )

    print(
        "[DISCORD] Created category: "
        "🚨 ALERTS"
    )

    return category


# ============================================================
# FIND EXISTING CHANNEL
# ============================================================

def find_channel(
    guild,
    desired_name
):

    normalized_desired = (
        normalize_channel_name(
            desired_name
        )
    )

    for channel in guild.text_channels:

        channel_name = (
            normalize_channel_name(
                channel.name
            )
        )

        if channel_name == normalized_desired:

            return channel

    return None


# ============================================================
# GET OR CREATE INTELLIGENCE CHANNEL
# ============================================================

async def get_intelligence_channel(
    guild,
    intelligence_type
):

    desired_name = (
        INTELLIGENCE_CHANNELS.get(
            intelligence_type,
            INTELLIGENCE_CHANNELS["general"]
        )
    )

    existing = find_channel(
        guild,
        desired_name
    )

    if existing:

        return existing

    category = (
        await get_intelligence_category(
            guild
        )
    )

    channel = (
        await guild.create_text_channel(
            desired_name,
            category=category,
            topic=(
                "ASNA Pakistan Intelligence "
                f"{intelligence_type} intelligence."
            ),
        )
    )

    print(
        f"[DISCORD] Created intelligence channel: "
        f"#{desired_name}"
    )

    return channel


# ============================================================
# GET OR CREATE SEVERITY CHANNEL
# ============================================================

async def get_severity_channel(
    guild,
    severity
):

    desired_name = (
        SEVERITY_CHANNELS.get(
            severity,
            "news-updates"
        )
    )

    existing = find_channel(
        guild,
        desired_name
    )

    if existing:

        return existing

    category = (
        await get_alert_category(
            guild
        )
    )

    channel = (
        await guild.create_text_channel(
            desired_name,
            category=category,
            topic=(
                "ASNA Pakistan Intelligence "
                f"{severity} alerts."
            ),
        )
    )

    print(
        f"[DISCORD] Created alert channel: "
        f"#{desired_name}"
    )

    return channel


# ============================================================
# SAFE ROW VALUE
# ============================================================

def safe_value(
    row,
    column,
    default=""
):

    if row is None:

        return default

    try:

        value = row[column]

    except (
        KeyError,
        IndexError,
    ):

        return default

    if value is None:

        return default

    value = str(value).strip()

    if not value:

        return default

    return value


# ============================================================
# TRUNCATE
# ============================================================

def truncate(
    text,
    maximum
):

    if not text:

        return ""

    text = str(text)

    if len(text) <= maximum:

        return text

    return (
        text[:maximum - 3]
        + "..."
    )


# ============================================================
# EVENT TYPE → CHANNEL
# ============================================================

def get_intelligence_type(
    category
):

    if not category:

        return "general"

    category = (
        str(category)
        .lower()
        .strip()
    )

    return EVENT_CHANNEL_MAP.get(
        category,
        "general"
    )


# ============================================================
# GET PENDING ALERTS
# ============================================================

def get_pending_alerts():

    db = get_database_connection()

    try:

        rows = db.execute(
            """
            SELECT

                a.id AS alert_id,

                a.event_id,

                a.alert_type,

                a.severity,

                a.score,

                a.headline AS alert_headline,

                a.reason,

                a.category AS alert_category,

                a.direction,

                a.channel_id,

                a.sent_at,

                a.status AS alert_status,

                e.event_hash,

                e.headline AS event_headline,

                e.summary AS event_summary,

                e.category AS event_category,

                e.subcategory,

                e.importance AS event_importance,

                e.confidence AS event_confidence,

                e.first_seen,

                e.last_updated,

                e.status AS event_status

            FROM alerts a

            INNER JOIN events e
                ON e.id = a.event_id

            WHERE
                a.sent_at IS NULL

            ORDER BY

                CASE a.severity

                    WHEN 'BREAKING' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4

                    ELSE 5

                END,

                a.score DESC,

                a.id ASC

            LIMIT ?

            """,
            (
                MAX_ALERTS_PER_RUN,
            ),
        ).fetchall()

        return rows

    finally:

        db.close()


# ============================================================
# GET IMPACT ANALYSIS
# ============================================================

def get_analysis(
    db,
    event_id
):

    return db.execute(
        """
        SELECT *

        FROM analyses

        WHERE event_id = ?

        ORDER BY id DESC

        LIMIT 1
        """,
        (
            event_id,
        )
    ).fetchone()


# ============================================================
# ADD IMPACT FIELD
# ============================================================

def add_impact_field(
    embed,
    title,
    value
):

    if not value:

        return

    embed.add_field(

        name=title,

        value=truncate(
            value,
            1024
        ),

        inline=False,

    )


# ============================================================
# BUILD EMBED
# ============================================================

def build_embed(
    alert,
    event,
    analysis
):

    severity = (
        safe_value(
            alert,
            "severity",
            "LOW"
        )
        .upper()
    )

    color = SEVERITY_COLORS.get(
        severity,
        discord.Color.blurple()
    )

    prefixes = {

        "BREAKING":
            "🚨 BREAKING",

        "HIGH":
            "🔴 HIGH IMPACT",

        "MEDIUM":
            "🟠 IMPORTANT",

        "LOW":
            "🟢 NEWS",

    }

    prefix = prefixes.get(
        severity,
        "📰 NEWS"
    )

    headline = (
        safe_value(
            event,
            "event_headline"
        )
        or safe_value(
            alert,
            "alert_headline"
        )
        or "Pakistan Intelligence Update"
    )

    headline = truncate(
        headline,
        230
    )

    summary = (
        safe_value(
            event,
            "event_summary"
        )
        or safe_value(
            alert,
            "reason"
        )
        or "Pakistan intelligence update."
    )

    summary = truncate(
        summary,
        4000
    )

    embed = discord.Embed(

        title=(
            f"{prefix} | {headline}"
        ),

        description=summary,

        color=color,

        timestamp=datetime.now(
            timezone.utc
        ),

    )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    category = (
        safe_value(
            event,
            "event_category"
        )
        or safe_value(
            alert,
            "alert_category"
        )
        or "general"
    )

    category_display = (
        category
        .replace("_", " ")
        .title()
    )

    embed.add_field(

        name="📌 Intelligence Type",

        value=category_display,

        inline=True,

    )

    # --------------------------------------------------------
    # SUBCATEGORY
    # --------------------------------------------------------

    subcategory = safe_value(
        event,
        "subcategory"
    )

    if subcategory:

        embed.add_field(

            name="🏷️ Subcategory",

            value=(
                subcategory
                .replace("_", " ")
                .title()
            ),

            inline=True,

        )

    # --------------------------------------------------------
    # DIRECTION
    # --------------------------------------------------------

    direction = (
        safe_value(
            alert,
            "direction"
        )
        or "neutral"
    )

    embed.add_field(

        name="📊 Direction",

        value=direction.title(),

        inline=True,

    )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = safe_value(
        alert,
        "score"
    )

    embed.add_field(

        name="⚡ Intelligence Score",

        value=(
            f"{score}/100"
            if score
            else "N/A"
        ),

        inline=True,

    )

    # --------------------------------------------------------
    # IMPORTANCE
    # --------------------------------------------------------

    importance = safe_value(
        event,
        "event_importance"
    )

    if importance:

        embed.add_field(

            name="🎯 Event Importance",

            value=f"{importance}/5",

            inline=True,

        )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    confidence = safe_value(
        event,
        "event_confidence"
    )

    if confidence:

        try:

            confidence_float = float(
                confidence
            )

            if confidence_float <= 1:

                confidence_display = (
                    f"{confidence_float:.0%}"
                )

            else:

                confidence_display = (
                    f"{confidence_float:.0f}%"
                )

            embed.add_field(

                name="🔎 Confidence",

                value=confidence_display,

                inline=True,

            )

        except ValueError:

            pass

    # ========================================================
    # IMPACT ANALYSIS
    # ========================================================

    if analysis:

        add_impact_field(
            embed,
            "💼 Business Impact",
            safe_value(
                analysis,
                "business_impact"
            )
        )

        add_impact_field(
            embed,
            "👥 Consumer Impact",
            safe_value(
                analysis,
                "consumer_impact"
            )
        )

        add_impact_field(
            embed,
            "🌐 Economic Impact",
            safe_value(
                analysis,
                "economic_impact"
            )
        )

        add_impact_field(
            embed,
            "📈 Market Impact",
            safe_value(
                analysis,
                "market_impact"
            )
        )

        add_impact_field(
            embed,
            "🏛️ Government Impact",
            safe_value(
                analysis,
                "government_impact"
            )
        )

        add_impact_field(
            embed,
            "💱 Currency Impact",
            safe_value(
                analysis,
                "currency_impact"
            )
        )

        add_impact_field(
            embed,
            "👷 Employment Impact",
            safe_value(
                analysis,
                "employment_impact"
            )
        )

        add_impact_field(
            embed,
            "🏦 Banking Impact",
            safe_value(
                analysis,
                "banking_impact"
            )
        )

    # ========================================================
    # CLASSIFICATION REASON
    # ========================================================

    reason = safe_value(
        alert,
        "reason"
    )

    if reason:

        embed.add_field(

            name="🧠 Classification Reason",

            value=truncate(
                reason,
                1024
            ),

            inline=False,

        )

    # ========================================================
    # UPDATED
    # ========================================================

    last_updated = safe_value(
        event,
        "last_updated"
    )

    if last_updated:

        embed.add_field(

            name="🕐 Updated",

            value=last_updated,

            inline=False,

        )

    # ========================================================
    # FOOTER
    # ========================================================

    embed.set_footer(

        text=(
            "ASNA Pakistan Intelligence • "
            "Automated Intelligence System"
        )

    )

    return embed


# ============================================================
# MARK ALERT SENT
# ============================================================

def mark_alert_sent(
    alert_id,
    channel_ids
):

    db = get_database_connection()

    try:

        if isinstance(
            channel_ids,
            (list, tuple)
        ):

            channel_value = ",".join(
                str(x)
                for x in channel_ids
            )

        else:

            channel_value = str(
                channel_ids
            )

        db.execute(
            """
            UPDATE alerts

            SET

                channel_id = ?,

                sent_at = CURRENT_TIMESTAMP,

                status = 'sent'

            WHERE id = ?

            """,
            (
                channel_value,
                alert_id,
            )
        )

        db.commit()

    finally:

        db.close()


# ============================================================
# MARK ALERT FAILED
# ============================================================

def mark_alert_failed(
    alert_id
):

    db = get_database_connection()

    try:

        db.execute(
            """
            UPDATE alerts

            SET status = 'failed'

            WHERE id = ?

            """,
            (
                alert_id,
            )
        )

        db.commit()

    finally:

        db.close()


# ============================================================
# REPORT ALERTS
# ============================================================

async def report_alerts():

    print()
    print("=" * 70)
    print("ASNA DISCORD INTELLIGENCE REPORTER")
    print("=" * 70)

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    if not verify_database():

        return

    # --------------------------------------------------------
    # GUILD
    # --------------------------------------------------------

    guild = get_guild()

    if guild is None:

        print(
            "[ERROR] ASNA Consultancy server "
            "was not found."
        )

        print(
            f"Expected Guild ID: {GUILD_ID}"
        )

        return

    print(
        f"[DISCORD] Server: {guild.name}"
    )

    print(
        f"[DISCORD] Server ID: {guild.id}"
    )

    # --------------------------------------------------------
    # PENDING ALERTS
    # --------------------------------------------------------

    alerts = get_pending_alerts()

    print()
    print(
        f"Pending alerts: {len(alerts)}"
    )

    if not alerts:

        print(
            "[DISCORD] No pending alerts."
        )

        return

    db = get_database_connection()

    sent = 0

    errors = 0

    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    for index, alert in enumerate(
        alerts,
        start=1
    ):

        try:

            severity = (
                safe_value(
                    alert,
                    "severity",
                    "LOW"
                )
                .upper()
            )

            # ------------------------------------------------
            # Determine intelligence category
            # ------------------------------------------------

            event_category = (
                safe_value(
                    alert,
                    "event_category"
                )
                or safe_value(
                    alert,
                    "alert_category"
                )
                or "general"
            )

            intelligence_type = (
                get_intelligence_type(
                    event_category
                )
            )

            # ------------------------------------------------
            # Intelligence channel
            # ------------------------------------------------

            intelligence_channel = (
                await get_intelligence_channel(
                    guild,
                    intelligence_type
                )
            )

            # ------------------------------------------------
            # Impact analysis
            # ------------------------------------------------

            analysis = get_analysis(
                db,
                alert["event_id"]
            )

            # ------------------------------------------------
            # Event information
            # ------------------------------------------------

            event = {

                "event_headline":
                    safe_value(
                        alert,
                        "event_headline"
                    ),

                "event_summary":
                    safe_value(
                        alert,
                        "event_summary"
                    ),

                "event_category":
                    safe_value(
                        alert,
                        "event_category"
                    ),

                "subcategory":
                    safe_value(
                        alert,
                        "subcategory"
                    ),

                "event_importance":
                    safe_value(
                        alert,
                        "event_importance"
                    ),

                "event_confidence":
                    safe_value(
                        alert,
                        "event_confidence"
                    ),

                "last_updated":
                    safe_value(
                        alert,
                        "last_updated"
                    ),

            }

            # ------------------------------------------------
            # Build embed
            # ------------------------------------------------

            embed = build_embed(
                alert,
                event,
                analysis,
            )

            # ------------------------------------------------
            # Primary intelligence channel
            # ------------------------------------------------

            await intelligence_channel.send(
                embed=embed
            )

            channel_ids = [
                intelligence_channel.id
            ]

            # ------------------------------------------------
            # BREAKING / HIGH secondary channel
            # ------------------------------------------------

            if severity in (
                "BREAKING",
                "HIGH",
            ):

                severity_channel = (
                    await get_severity_channel(
                        guild,
                        severity
                    )
                )

                # Send a second copy to severity alert channel.
                await severity_channel.send(
                    embed=embed
                )

                channel_ids.append(
                    severity_channel.id
                )

            # ------------------------------------------------
            # Mark sent
            # ------------------------------------------------

            mark_alert_sent(
                alert["alert_id"],
                channel_ids
            )

            sent += 1

            headline_preview = safe_value(
                alert,
                "event_headline"
            )

            headline_preview = truncate(
                headline_preview,
                65
            )

            print(
                f"[{index}/{len(alerts)}] "
                f"{severity:8} → "
                f"#{intelligence_channel.name} → "
                f"{headline_preview}"
            )

            # ------------------------------------------------
            # Discord rate-limit safety
            # ------------------------------------------------

            await asyncio.sleep(
                1
            )

        except Exception as error:

            errors += 1

            print(
                f"[ERROR] Alert "
                f"{alert['alert_id']}: "
                f"{error}"
            )

            try:

                mark_alert_failed(
                    alert["alert_id"]
                )

            except Exception:

                pass

    db.close()

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("DISCORD REPORTING COMPLETE")
    print("=" * 70)

    print(
        f"Alerts processed:   {len(alerts)}"
    )

    print(
        f"Successfully sent:  {sent}"
    )

    print(
        f"Errors:             {errors}"
    )

    print("=" * 70)


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print()
    print("=" * 70)
    print("ASNA DISCORD REPORTER ONLINE")
    print("=" * 70)

    print(
        f"Bot: {bot.user}"
    )

    print(
        f"Guilds: {len(bot.guilds)}"
    )

    try:

        await report_alerts()

    except Exception as error:

        print()
        print(
            "[FATAL] Reporter failed:"
        )

        print(
            error
        )

    finally:

        print()
        print(
            "[SYSTEM] Reporter finished."
        )

        await bot.close()


# ============================================================
# MAIN
# ============================================================

def main():

    if not TOKEN:

        print(
            "[ERROR] DISCORD_TOKEN is missing "
            "from .env"
        )

        return

    print(
        "[SYSTEM] Starting Discord Reporter..."
    )

    bot.run(
        TOKEN
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()