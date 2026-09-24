import os
import asyncio
import aiosqlite
import discord

from discord.ext import commands
from dotenv import load_dotenv

from database.database import (
    initialize_database,
    database_exists,
    get_database_stats
)

from news.sources import PAKISTAN_SOURCES


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing from your .env file."
    )


# ============================================================
# DATABASE
# ============================================================

DATABASE_PATH = os.path.join(
    "data",
    "intelligence.db"
)


# ============================================================
# DISCORD SERVER STRUCTURE
# ============================================================

SERVER_STRUCTURE = {

    "💰 BUSINESS & FINANCE": [
        "business-news",
        "finance-news",
        "economy",
        "banking",
        "tax-fbr",
        "corporate",
        "psx",
        "forex",
        "energy",
        "oil-gas",
        "trade-exports",
        "commodities",
        "agriculture",
        "textile",
        "cement",
        "real-estate",
        "technology",
    ],

    "🏛️ CURRENT AFFAIRS": [
        "national",
        "government",
        "politics",
        "judiciary",
        "security",
        "provincial",
        "international",
    ],

    "🚨 ALERTS": [
        "breaking-news",
        "business-alerts",
        "finance-alerts",
        "national-alerts",
    ],

    "📊 REPORTS": [
        "hourly",
        "morning",
        "evening",
        "weekly",
        "monthly",
    ],

    "📈 MARKETS": [
        "market-summary",
        "psx-data",
        "currency",
        "commodities",
        "economic-indicators",
    ],

    "🔎 RESEARCH": [
        "research",
        "search",
        "analysis",
    ],

    "🤖 SYSTEM": [
        "bot-status",
        "source-status",
        "bot-logs",
    ],
}


# ============================================================
# ROLES
# ============================================================

ROLES = [

    (
        "👑 ASNA Owner",
        discord.Colour.gold()
    ),

    (
        "🛡️ ASNA Administrator",
        discord.Colour.red()
    ),

    (
        "📊 ASNA Analyst",
        discord.Colour.blue()
    ),

    (
        "📰 ASNA News Editor",
        discord.Colour.green()
    ),

    (
        "🤖 ASNA Intelligence Bot",
        discord.Colour.purple()
    ),
]


# ============================================================
# BOT
# ============================================================

class ASNABot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.default()

        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self.commands_synced = False


    # ========================================================
    # SETUP HOOK
    # ========================================================

    async def setup_hook(self):

        print(
            "[DISCORD] Bot initialization complete."
        )

        print(
            "[DISCORD] Waiting for Discord gateway..."
        )


    # ========================================================
    # READY EVENT
    # ========================================================

    async def on_ready(self):

        print()
        print("=" * 65)
        print("ASNA PAKISTAN INTELLIGENCE")
        print("=" * 65)

        print(
            f"Bot: {self.user}"
        )

        print(
            f"Bot ID: {self.user.id}"
        )

        print(
            f"Servers: {len(self.guilds)}"
        )

        for guild in self.guilds:

            print(
                f"  └─ {guild.name} "
                f"({guild.id})"
            )

        print(
            "Status: ONLINE"
        )

        print("=" * 65)


        # Prevent duplicate synchronization
        if self.commands_synced:

            return


        # ====================================================
        # SLASH COMMAND SYNCHRONIZATION
        # ====================================================

        print(
            "[DISCORD] Synchronizing slash commands..."
        )


        total_synced = 0


        if not self.guilds:

            print(
                "[DISCORD] WARNING: "
                "No servers found after connection."
            )

            return


        for guild in self.guilds:

            try:

                # Copy all locally defined commands
                # into this specific guild.

                self.tree.copy_global_to(
                    guild=guild
                )


                # Guild synchronization is almost
                # immediate during development.

                synced = await self.tree.sync(
                    guild=guild
                )


                total_synced += len(
                    synced
                )


                print(
                    f"[DISCORD] Synced "
                    f"{len(synced)} commands to "
                    f"'{guild.name}'"
                )


            except Exception as error:

                print(
                    f"[DISCORD] Sync error "
                    f"for '{guild.name}':"
                )

                print(
                    repr(error)
                )


        self.commands_synced = True


        print(
            f"[DISCORD] Total commands synced: "
            f"{total_synced}"
        )

        print(
            "[DISCORD] Slash commands are ready."
        )

        print()


# ============================================================
# CREATE BOT
# ============================================================

bot = ASNABot()


# ============================================================
# GENERAL HELPERS
# ============================================================

def find_category(
    guild,
    name
):

    return discord.utils.get(
        guild.categories,
        name=name
    )


def find_channel(
    guild,
    name
):

    return discord.utils.get(
        guild.text_channels,
        name=name
    )


def find_role(
    guild,
    name
):

    return discord.utils.get(
        guild.roles,
        name=name
    )


# ============================================================
# SERVER AUDIT
# ============================================================

def audit_server(guild):

    existing_categories = {
        category.name
        for category in guild.categories
    }

    existing_channels = {
        channel.name
        for channel in guild.text_channels
    }

    existing_roles = {
        role.name
        for role in guild.roles
    }


    required_categories = set(
        SERVER_STRUCTURE.keys()
    )


    required_channels = {
        channel
        for channels in SERVER_STRUCTURE.values()
        for channel in channels
    }


    required_roles = {
        role[0]
        for role in ROLES
    }


    missing_categories = (
        required_categories
        - existing_categories
    )


    missing_channels = (
        required_channels
        - existing_channels
    )


    missing_roles = (
        required_roles
        - existing_roles
    )


    return {

        "required_categories":
            len(required_categories),

        "existing_categories":
            len(
                required_categories
                & existing_categories
            ),

        "missing_categories":
            missing_categories,


        "required_channels":
            len(required_channels),

        "existing_channels":
            len(
                required_channels
                & existing_channels
            ),

        "missing_channels":
            missing_channels,


        "required_roles":
            len(required_roles),

        "existing_roles":
            len(
                required_roles
                & existing_roles
            ),

        "missing_roles":
            missing_roles,
    }


# ============================================================
# CREATE ROLES
# ============================================================

async def repair_roles(guild):

    created = 0


    for name, colour in ROLES:

        if find_role(
            guild,
            name
        ):

            continue


        try:

            await guild.create_role(

                name=name,

                colour=colour,

                reason=(
                    "ASNA Intelligence "
                    "automatic setup"
                )

            )

            created += 1

            await asyncio.sleep(
                0.5
            )


        except discord.HTTPException as error:

            print(
                f"[ROLE ERROR] "
                f"{name}: {error}"
            )


    return created


# ============================================================
# CREATE CATEGORIES
# ============================================================

async def repair_categories(guild):

    created = 0


    for category_name in SERVER_STRUCTURE:

        if find_category(
            guild,
            category_name
        ):

            continue


        try:

            await guild.create_category(

                category_name,

                reason=(
                    "ASNA Intelligence "
                    "automatic setup"
                )

            )

            created += 1

            await asyncio.sleep(
                0.5
            )


        except discord.HTTPException as error:

            print(
                f"[CATEGORY ERROR] "
                f"{category_name}: {error}"
            )


    return created


# ============================================================
# CREATE CHANNELS
# ============================================================

async def repair_channels(guild):

    created = 0


    for category_name, channel_names in (
        SERVER_STRUCTURE.items()
    ):

        category = find_category(
            guild,
            category_name
        )


        if category is None:

            continue


        for channel_name in channel_names:

            existing = discord.utils.get(

                category.text_channels,

                name=channel_name

            )


            if existing:

                continue


            try:

                await guild.create_text_channel(

                    channel_name,

                    category=category,

                    reason=(
                        "ASNA Intelligence "
                        "automatic setup"
                    )

                )

                created += 1

                await asyncio.sleep(
                    0.5
                )


            except discord.HTTPException as error:

                print(
                    f"[CHANNEL ERROR] "
                    f"{channel_name}: {error}"
                )


    return created


# ============================================================
# COMPLETE REPAIR ENGINE
# ============================================================

async def run_repair(guild):

    print(
        "[SETUP] Checking roles..."
    )

    roles = await repair_roles(
        guild
    )


    print(
        "[SETUP] Checking categories..."
    )

    categories = await repair_categories(
        guild
    )


    print(
        "[SETUP] Checking channels..."
    )

    channels = await repair_channels(
        guild
    )


    return (
        roles,
        categories,
        channels
    )


# ============================================================
# DATABASE SOURCE REGISTRATION
# ============================================================

async def register_sources():

    if not database_exists():

        await initialize_database()


    os.makedirs(
        "data",
        exist_ok=True
    )


    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        for source in PAKISTAN_SOURCES:

            await db.execute(

                """
                INSERT OR IGNORE INTO sources
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
                    source["name"],
                    source["url"],
                    source["feed_url"],
                    source["source_type"],
                    source["category"],
                    source["priority"],
                )

            )


        await db.commit()


# ============================================================
# /PING
# ============================================================

@bot.tree.command(
    name="ping",
    description="Check whether ASNA Intelligence is online."
)
async def ping(
    interaction: discord.Interaction
):

    latency = round(
        bot.latency * 1000
    )


    await interaction.response.send_message(

        "🟢 **ASNA Intelligence is online!**\n\n"
        f"Latency: `{latency} ms`"

    )


# ============================================================
# /STATUS
# ============================================================

@bot.tree.command(
    name="status",
    description="Show ASNA Intelligence system status."
)
async def status(
    interaction: discord.Interaction
):

    guild = interaction.guild


    audit = audit_server(
        guild
    )


    roles_ok = (
        audit["existing_roles"]
        ==
        audit["required_roles"]
    )


    categories_ok = (
        audit["existing_categories"]
        ==
        audit["required_categories"]
    )


    channels_ok = (
        audit["existing_channels"]
        ==
        audit["required_channels"]
    )


    database_ok = database_exists()


    await interaction.response.send_message(

        "## 🇵🇰 ASNA PAKISTAN INTELLIGENCE\n\n"

        "### DISCORD INFRASTRUCTURE\n\n"

        f"Roles: "
        f"`{audit['existing_roles']}/"
        f"{audit['required_roles']}` "
        f"{'🟢' if roles_ok else '🟡'}\n"

        f"Categories: "
        f"`{audit['existing_categories']}/"
        f"{audit['required_categories']}` "
        f"{'🟢' if categories_ok else '🟡'}\n"

        f"Channels: "
        f"`{audit['existing_channels']}/"
        f"{audit['required_channels']}` "
        f"{'🟢' if channels_ok else '🟡'}\n\n"

        "### INTELLIGENCE MODULES\n\n"

        f"🗄️ Database: "
        f"{'🟢 Online' if database_ok else '🔴 Not installed'}\n"

        "📰 News Collector: 🔴 Not installed\n"
        "♻️ Deduplication: 🔴 Not installed\n"
        "🏷️ Classification: 🔴 Not installed\n"
        "🧠 AI Analysis: 🔴 Not installed\n"
        "⏰ Scheduler: 🔴 Not installed\n"
        "📊 Market Engine: 🔴 Not installed\n"
        "🚨 Breaking News: 🔴 Not installed"

    )


# ============================================================
# /SETUP
# ============================================================

@bot.tree.command(
    name="setup",
    description="Create the complete ASNA Intelligence infrastructure."
)
async def setup(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(

            "❌ You need **Manage Server** permission.",

            ephemeral=True

        )

        return


    await interaction.response.send_message(

        "🚀 **ASNA Intelligence setup started.**\n\n"

        "The bot is auditing your server and "
        "creating anything that is missing.\n\n"

        "⏳ Setup is running in the background.",

        ephemeral=True

    )


    async def background_setup():

        try:

            (
                roles,
                categories,
                channels
            ) = await run_repair(
                interaction.guild
            )


            audit = audit_server(
                interaction.guild
            )


            await interaction.followup.send(

                "## 🟢 ASNA INTELLIGENCE SETUP COMPLETE\n\n"

                f"👥 Roles created: `{roles}`\n"
                f"📁 Categories created: `{categories}`\n"
                f"📺 Channels created: `{channels}`\n\n"

                "### CURRENT STRUCTURE\n\n"

                f"Roles: "
                f"`{audit['existing_roles']}/"
                f"{audit['required_roles']}` "
                f"{'🟢' if not audit['missing_roles'] else '🟡'}\n"

                f"Categories: "
                f"`{audit['existing_categories']}/"
                f"{audit['required_categories']}` "
                f"{'🟢' if not audit['missing_categories'] else '🟡'}\n"

                f"Channels: "
                f"`{audit['existing_channels']}/"
                f"{audit['required_channels']}` "
                f"{'🟢' if not audit['missing_channels'] else '🟡'}",

                ephemeral=True

            )


        except Exception as error:

            print(
                "[SETUP ERROR]",
                repr(error)
            )


            try:

                await interaction.followup.send(

                    "❌ **Setup encountered an error.**\n\n"

                    f"```text\n"
                    f"{error}"
                    f"\n```",

                    ephemeral=True

                )

            except Exception:

                pass


    asyncio.create_task(
        background_setup()
    )


# ============================================================
# /REPAIR
# ============================================================

@bot.tree.command(
    name="repair",
    description="Audit and repair the ASNA Intelligence server."
)
async def repair(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(

            "❌ You need **Manage Server** permission.",

            ephemeral=True

        )

        return


    await interaction.response.send_message(

        "🔧 **ASNA repair started.**\n\n"

        "Checking roles, categories and channels...",

        ephemeral=True

    )


    async def background_repair():

        try:

            (
                roles,
                categories,
                channels
            ) = await run_repair(
                interaction.guild
            )


            audit = audit_server(
                interaction.guild
            )


            complete = not (

                audit["missing_roles"]
                or audit["missing_categories"]
                or audit["missing_channels"]

            )


            if complete:

                title = "## 🟢 REPAIR COMPLETE\n\n"

            else:

                title = (
                    "## 🟡 REPAIR PARTIALLY COMPLETE\n\n"
                )


            await interaction.followup.send(

                title

                + f"👥 Roles created: `{roles}`\n"

                + f"📁 Categories created: "
                f"`{categories}`\n"

                + f"📺 Channels created: "
                f"`{channels}`\n\n"

                + "### SERVER AUDIT\n\n"

                + f"Roles: "
                f"`{audit['existing_roles']}/"
                f"{audit['required_roles']}`\n"

                + f"Categories: "
                f"`{audit['existing_categories']}/"
                f"{audit['required_categories']}`\n"

                + f"Channels: "
                f"`{audit['existing_channels']}/"
                f"{audit['required_channels']}`",

                ephemeral=True

            )


        except Exception as error:

            print(
                "[REPAIR ERROR]",
                repr(error)
            )


            await interaction.followup.send(

                "❌ **Repair failed.**\n\n"

                f"```text\n"
                f"{error}"
                f"\n```",

                ephemeral=True

            )


    asyncio.create_task(
        background_repair()
    )


# ============================================================
# /CHANNELS
# ============================================================

@bot.tree.command(
    name="channels",
    description="Show ASNA channel installation status."
)
async def channels(
    interaction: discord.Interaction
):

    audit = audit_server(
        interaction.guild
    )


    missing = audit[
        "missing_channels"
    ]


    if not missing:

        await interaction.response.send_message(

            "🟢 **All ASNA channels are installed.**\n\n"

            f"`{audit['existing_channels']}/"
            f"{audit['required_channels']}` "
            "channels ready."

        )

        return


    missing_text = "\n".join(

        f"❌ #{channel}"

        for channel in sorted(
            missing
        )

    )


    await interaction.response.send_message(

        "## 🟡 CHANNEL AUDIT\n\n"

        f"Installed: "
        f"`{audit['existing_channels']}/"
        f"{audit['required_channels']}`\n\n"

        "### Missing\n\n"

        f"{missing_text}\n\n"

        "Run `/repair` to create them automatically.",

        ephemeral=True

    )


# ============================================================
# /INITIALIZE
# ============================================================

@bot.tree.command(
    name="initialize",
    description="Initialize the ASNA Intelligence database."
)
async def initialize(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(

            "❌ You need **Manage Server** permission.",

            ephemeral=True

        )

        return


    await interaction.response.send_message(

        "⚙️ **Initializing ASNA Intelligence...**\n\n"

        "🗄️ Creating database...\n"
        "📡 Registering Pakistan sources...\n"
        "⚙️ Configuring system...",

        ephemeral=True

    )


    async def background_initialize():

        try:

            await initialize_database()

            await register_sources()

            stats = await get_database_stats()


            await interaction.followup.send(

                "## 🟢 DATABASE INITIALIZED\n\n"

                "🗄️ SQLite Database: 🟢 Ready\n"

                f"📡 News Sources: `{stats['sources']}`\n"

                f"📰 Articles: `{stats['articles']}`\n"

                f"🔥 Events: `{stats['events']}`\n"

                f"🧠 Analyses: `{stats['analysis']}`\n\n"

                "### SYSTEM\n"

                "Database: 🟢\n"
                "Source Registry: 🟢\n\n"

                "### NEXT MODULES\n"

                "📰 News Collector\n"
                "♻️ Duplicate Detection\n"
                "🏷️ News Classification\n"
                "🧠 AI Analysis",

                ephemeral=True

            )


        except Exception as error:

            print(
                "[DATABASE ERROR]",
                repr(error)
            )


            await interaction.followup.send(

                "❌ **Database initialization failed.**\n\n"

                f"```text\n"
                f"{error}"
                f"\n```",

                ephemeral=True

            )


    asyncio.create_task(
        background_initialize()
    )


# ============================================================
# /DB-STATUS
# ============================================================

@bot.tree.command(
    name="db-status",
    description="Show ASNA Intelligence database status."
)
async def db_status(
    interaction: discord.Interaction
):

    if not database_exists():

        await interaction.response.send_message(

            "🔴 **Database is not initialized.**\n\n"

            "Run `/initialize` first.",

            ephemeral=True

        )

        return


    try:

        stats = await get_database_stats()


        await interaction.response.send_message(

            "## 🗄️ ASNA DATABASE STATUS\n\n"

            "Database: 🟢 Online\n\n"

            f"📡 Sources: `{stats['sources']}`\n"
            f"📰 Articles: `{stats['articles']}`\n"
            f"🔥 Events: `{stats['events']}`\n"
            f"🧠 Analyses: `{stats['analysis']}`\n"
            f"📊 Market Records: `{stats['market_data']}`\n"
            f"🚨 Alerts: `{stats['alerts']}`\n"
            f"📑 Reports: `{stats['reports']}`"

        )


    except Exception as error:

        await interaction.response.send_message(

            "❌ Database status error:\n"

            f"```text\n"
            f"{error}\n"
            f"```",

            ephemeral=True

        )


# ============================================================
# COMMAND ERROR HANDLER
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction,
    error
):

    print()
    print(
        "[COMMAND ERROR]"
    )

    print(
        repr(error)
    )


    try:

        if interaction.response.is_done():

            await interaction.followup.send(

                "❌ An unexpected command error occurred.\n"
                "Check PowerShell for details.",

                ephemeral=True

            )

        else:

            await interaction.response.send_message(

                "❌ An unexpected command error occurred.\n"
                "Check PowerShell for details.",

                ephemeral=True

            )


    except Exception:

        pass


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "[SYSTEM] Starting ASNA Pakistan Intelligence..."
    )

    bot.run(
        TOKEN
    )