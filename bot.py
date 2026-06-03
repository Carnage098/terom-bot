import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os

from database import init_db
from permissions import is_staff

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

@bot.event
async def on_ready():

    await init_db()

    try:

        synced = await bot.tree.sync()

        print(
            f"{len(synced)} commandes synchronisées"
        )

    except Exception as e:

        print(e)

    print(
        f"Connecté en tant que {bot.user}"
    ) 
# ==================================
# REGISTER
# ==================================

@bot.tree.command(
    name="register",
    description="S'inscrire au tournoi"
)
@app_commands.describe(
    deck="Deck joué (facultatif)"
)
async def register(
    interaction: discord.Interaction,
    deck: str = None
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
                deck,
                team_name
            )
            VALUES (?, ?, ?, NULL)
            """,
            (
                str(interaction.user.id),
                interaction.user.name,
                deck
            )
        )

        await db.commit()

    await interaction.response.send_message(
        "✅ Inscription réussie."
    )

# ==================================
# UNREGISTER
# ==================================

@bot.tree.command(
    name="unregister",
    description="Se désinscrire du tournoi"
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
# ==================================
# ADD PLAYER
# ==================================

@bot.tree.command(
    name="add_player",
    description="Ajouter un joueur"
)
async def add_player(
    interaction: discord.Interaction,
    player: discord.Member
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )

        return

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO players(
                discord_id,
                username,
                deck,
                team_name
            )
            VALUES (?, ?, NULL, NULL)
            """,
            (
                str(player.id),
                player.name
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ {player.mention} ajouté."
    )

# ==================================
# REMOVE PLAYER
# ==================================

@bot.tree.command(
    name="remove_player",
    description="Retirer un joueur"
)
async def remove_player(
    interaction: discord.Interaction,
    player: discord.Member
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )

        return

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            """
            DELETE FROM players
            WHERE discord_id = ?
            """,
            (str(player.id),)
        )

        await db.commit()

    await interaction.response.send_message(
        f"🗑️ {player.mention} retiré."
    )
    # ==================================
# ASSIGN TEAM
# ==================================

@bot.tree.command(
    name="assign_team",
    description="Attribuer une équipe"
)
async def assign_team(
    interaction: discord.Interaction,
    player: discord.Member,
    team: str
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )

        return

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            """
            UPDATE players
            SET team_name = ?
            WHERE discord_id = ?
            """,
            (
                team,
                str(player.id)
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ {player.mention} rejoint {team}"
    )
    # ==================================
# LEADERBOARD
# ==================================

@bot.tree.command(
    name="leaderboard",
    description="Classement des équipes"
)
async def leaderboard(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT name, points
            FROM teams
            ORDER BY points DESC
            """
        )

        teams = await cursor.fetchall()

    if not teams:

        await interaction.response.send_message(
            "❌ Aucune équipe."
        )

        return

    msg = "🏆 Classement Ulti-Mate\n\n"

    for index, team in enumerate(
        teams,
        start=1
    ):

        msg += (
            f"{index}. "
            f"{team[0]} - "
            f"{team[1]} pts\n"
        )

    await interaction.response.send_message(msg)
 
    bot.run(TOKEN)
