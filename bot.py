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

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await init_db()
    synced = await bot.tree.sync()
    print(f"{len(synced)} commandes synchronisées")
    print(f"Connecté en tant que {bot.user}")

@bot.tree.command(name="register", description="S'inscrire au tournoi")
async def register(interaction: discord.Interaction, deck: str = None):
    async with aiosqlite.connect("database.db") as db:
        cur = await db.execute(
            "SELECT discord_id FROM players WHERE discord_id=?",
            (str(interaction.user.id),)
        )
        if await cur.fetchone():
            await interaction.response.send_message("❌ Déjà inscrit.", ephemeral=True)
            return

        await db.execute(
            "INSERT INTO players(discord_id, username, deck, team_name) VALUES(?,?,?,NULL)",
            (str(interaction.user.id), interaction.user.name, deck)
        )
        await db.commit()

    await interaction.response.send_message("✅ Inscription réussie.")

@bot.tree.command(name="unregister", description="Se désinscrire")
async def unregister(interaction: discord.Interaction):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "DELETE FROM players WHERE discord_id=?",
            (str(interaction.user.id),)
        )
        await db.commit()

    await interaction.response.send_message("🗑️ Désinscription effectuée.")

@bot.tree.command(name="create_team", description="Créer une équipe")
async def create_team(interaction: discord.Interaction, name: str):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return

    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "INSERT INTO teams(name, points) VALUES(?,0)",
            (name,)
        )
        await db.commit()

    await interaction.response.send_message(f"🏆 Équipe créée : {name}")

@bot.tree.command(name="delete_team", description="Supprimer une équipe")
async def delete_team(interaction: discord.Interaction, name: str):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return

    async with aiosqlite.connect("database.db") as db:
        await db.execute("DELETE FROM teams WHERE name=?", (name,))
        await db.commit()

    await interaction.response.send_message(f"🗑️ Équipe supprimée : {name}")

@bot.tree.command(name="teams", description="Voir les équipes")
async def teams(interaction: discord.Interaction):
    async with aiosqlite.connect("database.db") as db:
        cur = await db.execute("SELECT name, points FROM teams ORDER BY points DESC")
        rows = await cur.fetchall()

    if not rows:
        await interaction.response.send_message("❌ Aucune équipe.")
        return

    msg = "🏆 Équipes\n\n"
    for name, points in rows:
        msg += f"• {name} ({points} pts)\n"

    await interaction.response.send_message(msg)

@bot.tree.command(name="leaderboard", description="Classement des équipes")
async def leaderboard(interaction: discord.Interaction):
    async with aiosqlite.connect("database.db") as db:
        cur = await db.execute("SELECT name, points FROM teams ORDER BY points DESC")
        rows = await cur.fetchall()

    msg = "🏆 Classement Ulti-Mate\n\n"
    for i, (name, points) in enumerate(rows, start=1):
        msg += f"{i}. {name} - {points} pts\n"

    await interaction.response.send_message(msg)

@bot.tree.command(name="add_player", description="Ajouter un joueur")
async def add_player(interaction: discord.Interaction, player: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return

    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO players(discord_id, username, deck, team_name) VALUES(?,?,NULL,NULL)",
            (str(player.id), player.name)
        )
        await db.commit()

    await interaction.response.send_message(f"✅ {player.mention} ajouté.")

@bot.tree.command(name="remove_player", description="Retirer un joueur")
async def remove_player(interaction: discord.Interaction, player: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return

    async with aiosqlite.connect("database.db") as db:
        await db.execute("DELETE FROM players WHERE discord_id=?", (str(player.id),))
        await db.commit()

    await interaction.response.send_message(f"🗑️ {player.mention} retiré.")

@bot.tree.command(name="assign_team", description="Attribuer une équipe")
async def assign_team(interaction: discord.Interaction, player: discord.Member, team: str):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return

    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE players SET team_name=? WHERE discord_id=?",
            (team, str(player.id))
        )
        await db.commit()

    await interaction.response.send_message(f"✅ {player.mention} rejoint {team}")

@bot.tree.command(name="add_points", description="Ajouter des points")
async def add_points(interaction: discord.Interaction, team: str, points: int):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return

    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE teams SET points = points + ? WHERE name=?",
            (points, team)
        )
        await db.commit()

    await interaction.response.send_message(f"➕ {points} point(s) ajouté(s) à {team}")

@bot.tree.command(name="remove_points", description="Retirer des points")
async def remove_points(interaction: discord.Interaction, team: str, points: int):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return

    async with aiosqlite.connect("database.db") as db:
        cur = await db.execute("SELECT points FROM teams WHERE name=?", (team,))
        row = await cur.fetchone()

        if not row:
            await interaction.response.send_message("❌ Équipe introuvable.")
            return

        new_points = max(0, row[0] - points)

        await db.execute(
            "UPDATE teams SET points=? WHERE name=?",
            (new_points, team)
        )
        await db.commit()

    await interaction.response.send_message(f"➖ {points} point(s) retiré(s) à {team}")

bot.run(TOKEN)

