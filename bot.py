import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --------------------
# DATABASE
# --------------------

async def init_db():
    async with aiosqlite.connect("database.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS tournaments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            active INTEGER
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players(
            discord_id TEXT,
            username TEXT,
            deck TEXT
        )
        """)

        await db.commit()

# --------------------
# EVENTS
# --------------------

@bot.event
async def on_ready():
    await init_db()

    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} commandes synchronisées")
    except Exception as e:
        print(e)

    print(f"Connecté en tant que {bot.user}")

# --------------------
# CREATE TOURNAMENT
# --------------------

@bot.tree.command(name="create_tournament")
@app_commands.describe(name="Nom du tournoi")
async def create_tournament(
    interaction: discord.Interaction,
    name: str
):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "Tu n'as pas la permission.",
            ephemeral=True
        )
        return

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE tournaments SET active = 0"
        )

        await db.execute(
            """
            INSERT INTO tournaments(name, active)
            VALUES(?, 1)
            """,
            (name,)
        )

        await db.commit()

    await interaction.response.send_message(
        f"🏆 Tournoi créé : **{name}**"
    )

# --------------------
# REGISTER
# --------------------

@bot.tree.command(name="register")
@app_commands.describe(deck="Nom du deck")
async def register(
    interaction: discord.Interaction,
    deck: str
):

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            """
            INSERT INTO players
            VALUES(?,?,?)
            """,
            (
                str(interaction.user.id),
                interaction.user.name,
                deck
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ {interaction.user.mention} inscrit avec le deck **{deck}**"
    )

# --------------------
# PLAYERS LIST
# --------------------

@bot.tree.command(name="players")
async def players(interaction: discord.Interaction):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            "SELECT username, deck FROM players"
        )

        players = await cursor.fetchall()

    if not players:
        await interaction.response.send_message(
            "Aucun joueur inscrit."
        )
        return

    message = ""

    for player in players:
        message += f"• {player[0]} ({player[1]})\n"

    await interaction.response.send_message(
        f"📋 Participants :\n\n{message}"
    )

bot.run(TOKEN)
