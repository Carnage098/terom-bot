import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os

TOKEN = os.getenv("DISCORD_TOKEN")

# ==================================
# CONFIGURATION
# ==================================

STAFF_ROLES = [
    "Admin",
    "🛑Modo"
]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ==================================
# PERMISSIONS
# ==================================

def is_staff(member):

    if member.guild_permissions.administrator:
        return True

    for role in member.roles:

        if role.name in STAFF_ROLES:
            return True

    return False

# ==================================
# BASE DE DONNÉES
# ==================================

async def init_db():

    async with aiosqlite.connect("database.db") as db:

        # --------------------------
        # TOURNOIS
        # --------------------------

        await db.execute("""
        CREATE TABLE IF NOT EXISTS tournaments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
        """)

        # --------------------------
        # TEAMS
        # --------------------------

        await db.execute("""
        CREATE TABLE IF NOT EXISTS teams(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            points INTEGER DEFAULT 0
        )
        """)

        # --------------------------
        # JOUEURS
        # --------------------------

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players(
            discord_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            deck TEXT,
            team_name TEXT
        )
        """)

        await db.commit()

# ==================================
# BOT READY
# ==================================

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
# CREATE TEAM
# ==================================

@bot.tree.command(
    name="create_team",
    description="Créer une équipe"
)
@app_commands.describe(
    name="Nom de l'équipe"
)
async def create_team(
    interaction: discord.Interaction,
    name: str
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )

        return

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM teams
            WHERE name = ?
            """,
            (name,)
        )

        existing = await cursor.fetchone()

        if existing:

            await interaction.response.send_message(
                "❌ Cette équipe existe déjà."
            )

            return

        await db.execute(
            """
            INSERT INTO teams(
                name,
                points
            )
            VALUES (?, 0)
            """,
            (name,)
        )

        await db.commit()

    await interaction.response.send_message(
        f"🏆 Équipe créée : **{name}**"
    )

# ==================================
# DELETE TEAM
# ==================================

@bot.tree.command(
    name="delete_team",
    description="Supprimer une équipe"
)
@app_commands.describe(
    name="Nom de l'équipe"
)
async def delete_team(
    interaction: discord.Interaction,
    name: str
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
            DELETE FROM teams
            WHERE name = ?
            """,
            (name,)
        )

        await db.commit()

    await interaction.response.send_message(
        f"🗑️ Équipe supprimée : **{name}**"
    )

# ==================================
# TEAMS
# ==================================

@bot.tree.command(
    name="teams",
    description="Voir toutes les équipes"
)
async def teams(
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

        teams_list = await cursor.fetchall()

    if not teams_list:

        await interaction.response.send_message(
            "❌ Aucune équipe."
        )

        return

    message = "🏆 Équipes\n\n"

    for team in teams_list:

        message += (
            f"• {team[0]} "
            f"({team[1]} pts)\n"
        )

    await interaction.response.send_message(
        message
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

        teams_list = await cursor.fetchall()

    if not teams_list:

        await interaction.response.send_message(
            "❌ Aucune équipe."
        )

        return

    classement = "🏆 Classement Ulti-Mate\n\n"

    for index, team in enumerate(
        teams_list,
        start=1
    ):

        classement += (
            f"{index}. "
            f"{team[0]} - "
            f"{team[1]} pts\n"
        )

    await interaction.response.send_message(
        classement
    )
    # ==================================
# ASSIGN TEAM
# ==================================

@bot.tree.command(
    name="assign_team",
    description="Assigner un joueur à une équipe"
)
@app_commands.describe(
    player="Joueur",
    team="Nom de l'équipe"
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

        cursor = await db.execute(
            "SELECT * FROM teams WHERE name = ?",
            (team,)
        )

        team_exists = await cursor.fetchone()

        if not team_exists:

            await interaction.response.send_message(
                "❌ Équipe introuvable."
            )
            return

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
        f"✅ {player.mention} rejoint **{team}**"
    )

# ==================================
# CHANGE TEAM
# ==================================

@bot.tree.command(
    name="change_team",
    description="Changer l'équipe d'un joueur"
)
@app_commands.describe(
    player="Joueur",
    team="Nouvelle équipe"
)
async def change_team(
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
        f"🔄 {player.mention} rejoint désormais **{team}**"
    )

# ==================================
# ADD PLAYER
# ==================================

@bot.tree.command(
    name="add_player",
    description="Ajouter un joueur"
)
@app_commands.describe(
    player="Joueur"
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

        cursor = await db.execute(
            """
            SELECT *
            FROM players
            WHERE discord_id = ?
            """,
            (str(player.id),)
        )

        existing = await cursor.fetchone()

        if existing:

            await interaction.response.send_message(
                "❌ Joueur déjà inscrit."
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
            VALUES (?, ?, NULL, NULL)
            """,
            (
                str(player.id),
                player.name
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ {player.mention} ajouté au tournoi."
    )

# ==================================
# REMOVE PLAYER
# ==================================

@bot.tree.command(
    name="remove_player",
    description="Retirer un joueur"
)
@app_commands.describe(
    player="Joueur"
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
        f"🗑️ {player.mention} retiré du tournoi."
    )

# ==================================
# ADD POINTS
# ==================================

@bot.tree.command(
    name="add_points",
    description="Ajouter des points à une équipe"
)
@app_commands.describe(
    team="Nom de l'équipe",
    points="Nombre de points"
)
async def add_points(
    interaction: discord.Interaction,
    team: str,
    points: int
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
            UPDATE teams
            SET points = points + ?
            WHERE name = ?
            """,
            (
                points,
                team
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"➕ {points} point(s) ajouté(s) à **{team}**"
    )

# ==================================
# REMOVE POINTS
# ==================================

@bot.tree.command(
    name="remove_points",
    description="Retirer des points à une équipe"
)
@app_commands.describe(
    team="Nom de l'équipe",
    points="Nombre de points"
)
async def remove_points(
    interaction: discord.Interaction,
    team: str,
    points: int
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )
        return

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT points
            FROM teams
            WHERE name = ?
            """,
            (team,)
        )

        result = await cursor.fetchone()

        if not result:

            await interaction.response.send_message(
                "❌ Équipe introuvable."
            )
            return

        current_points = result[0]

        new_points = max(
            0,
            current_points - points
        )

        await db.execute(
            """
            UPDATE teams
            SET points = ?
            WHERE name = ?
            """,
            (
                new_points,
                team
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"➖ {points} point(s) retiré(s) à **{team}**"
    ) 
