import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os

TOKEN = os.getenv("DISCORD_TOKEN")

# -----------------------------
# BOT CONFIG
# -----------------------------

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# -----------------------------
# DATABASE
# -----------------------------

async def init_db():

    async with aiosqlite.connect("database.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS tournaments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players(
            discord_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            deck TEXT NOT NULL
        )
        """)

        await db.commit()

# -----------------------------
# EVENTS
# -----------------------------

@bot.event
async def on_ready():

    await init_db()

    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} commandes synchronisées")
    except Exception as e:
        print(e)

    print(f"Connecté en tant que {bot.user}")

# -----------------------------
# CREATE TOURNAMENT
# -----------------------------

@bot.tree.command(
    name="create_tournament",
    description="Créer un tournoi"
)
@app_commands.describe(
    name="Nom du tournoi"
)
async def create_tournament(
    interaction: discord.Interaction,
    name: str
):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "❌ Permission refusée.",
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
            VALUES (?, 1)
            """,
            (name,)
        )

        await db.commit()

    await interaction.response.send_message(
        f"🏆 Tournoi créé : **{name}**"
    )

# -----------------------------
# CURRENT TOURNAMENT
# -----------------------------

@bot.tree.command(
    name="tournament",
    description="Afficher le tournoi actif"
)
async def tournament(interaction: discord.Interaction):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT id, name
            FROM tournaments
            WHERE active = 1
            """
        )

        tournament = await cursor.fetchone()

    if not tournament:
        await interaction.response.send_message(
            "❌ Aucun tournoi actif."
        )
        return

    await interaction.response.send_message(
        f"🏆 Tournoi actif : **{tournament[1]}** (ID {tournament[0]})"
    )

# -----------------------------
# REGISTER
# -----------------------------

@bot.tree.command(
    name="register",
    description="S'inscrire au tournoi"
)
@app_commands.describe(
    deck="Nom du deck joué"
)
async def register(
    interaction: discord.Interaction,
    deck: str
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM players
            WHERE discord_id = ?
            """,
            (str(interaction.user.id),)
        )

        existing = await cursor.fetchone()

        if existing:

            await interaction.response.send_message(
                "❌ Tu es déjà inscrit.",
                ephemeral=True
            )

            return

        await db.execute(
            """
            INSERT INTO players(
                discord_id,
                username,
                deck
            )
            VALUES (?, ?, ?)
            """,
            (
                str(interaction.user.id),
                interaction.user.name,
                deck
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ {interaction.user.mention} inscrit avec **{deck}**"
    )

# -----------------------------
# UNREGISTER
# -----------------------------

@bot.tree.command(
    name="unregister",
    description="Se désinscrire"
)
async def unregister(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            """
            DELETE FROM players
            WHERE discord_id = ?
            """,
            (str(interaction.user.id),)
        )

        await db.commit()

    await interaction.response.send_message(
        "🗑️ Désinscription effectuée."
    )

# -----------------------------
# PLAYERS
# -----------------------------

@bot.tree.command(
    name="players",
    description="Afficher les participants"
)
async def players(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT username, deck
            FROM players
            ORDER BY username
            """
        )

        players = await cursor.fetchall()

    if not players:

        await interaction.response.send_message(
            "❌ Aucun joueur inscrit."
        )

        return

    message = ""

    for username, deck in players:

        message += f"• {username} ({deck})\n"

    await interaction.response.send_message(
        f"📋 Participants\n\n{message}"
    )

# -----------------------------
# STANDINGS
# -----------------------------

@bot.tree.command(
    name="standings",
    description="Afficher le classement"
)
async def standings(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT username
            FROM players
            ORDER BY username
            """
        )

        players = await cursor.fetchall()

    if not players:

        await interaction.response.send_message(
            "❌ Aucun joueur."
        )

        return

    classement = "🏆 Classement\n\n"

    for index, player in enumerate(players, start=1):

        classement += f"{index}. {player[0]}\n"

    await interaction.response.send_message(
        classement
    )

# -----------------------------
# RUN
# -----------------------------

bot.run(TOKEN)
