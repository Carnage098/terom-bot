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
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)
async def team_autocomplete(
    interaction: discord.Interaction,
    current: str
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT name
            FROM teams
            ORDER BY name
            """
        )

        teams = await cursor.fetchall()

    return [
        app_commands.Choice(
            name=team[0],
            value=team[0]
        )
        for team in teams
        if current.lower() in team[0].lower()
    ][:25]
@bot.event
async def on_ready():

    await init_db()

    synced = await bot.tree.sync()

    print("✅ Base de données initialisée")
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
        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )
        return

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            "SELECT name FROM teams WHERE name = ?",
            (name,)
        )

        if await cursor.fetchone():
            await interaction.response.send_message(
                "❌ Cette équipe existe déjà.",
                ephemeral=True
            )
            return

        await db.execute(
            "INSERT INTO teams(name, points) VALUES(?, 0)",
            (name,)
        )

        await db.commit()

    await interaction.response.send_message(
        f"🏆 Équipe créée : {name}",
        ephemeral=True
    )
@bot.tree.command(name="delete_team", description="Supprimer une équipe")
@app_commands.autocomplete(name=team_autocomplete)
async def delete_team(
    interaction: discord.Interaction,
    name: str
):
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
        await interaction.response.send_message("❌ Aucune équipe.",
        ephemeral=True
        )
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

    await interaction.response.send_message(f"✅ {player.mention} ajouté.",
    ephemeral=True
    )

@bot.tree.command(name="remove_player", description="Retirer un joueur")
async def remove_player(interaction: discord.Interaction, player: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return

    async with aiosqlite.connect("database.db") as db:
        await db.execute("DELETE FROM players WHERE discord_id=?", (str(player.id),))
        await db.commit()

    await interaction.response.send_message(f"🗑️ {player.mention} retiré.",
    ephemeral=True
    )
@bot.tree.command(
    name="assign_team",
    description="Attribuer une équipe"
)
@app_commands.autocomplete(team=team_autocomplete)
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
            "SELECT 1 FROM teams WHERE name = ?",
            (team,)
        )

        if not await cursor.fetchone():
            await interaction.response.send_message(
                "❌ Cette équipe n'existe pas.",
                ephemeral=True
            )
            return

        await db.execute(
            "UPDATE players SET team_name=? WHERE discord_id=?",
            (team, str(player.id))
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ {player.mention} rejoint {team}"
    )
@bot.tree.command(
    name="add_points",
    description="Ajouter des points"
)
@app_commands.autocomplete(team=team_autocomplete)
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

        cursor = await db.execute(
            "SELECT 1 FROM teams WHERE name = ?",
            (team,)
        )

        if not await cursor.fetchone():
            await interaction.response.send_message(
                "❌ Cette équipe n'existe pas.",
                ephemeral=True
            )
            return

        await db.execute(
            "UPDATE teams SET points = points + ? WHERE name = ?",
            (points, team)
        )

        await db.commit()

    await interaction.response.send_message(
        f"➕ {points} point(s) ajouté(s) à {team}"
    )

@bot.tree.command(
    name="remove_points",
    description="Retirer des points"
)
@app_commands.autocomplete(team=team_autocomplete)
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
            "SELECT points FROM teams WHERE name = ?",
            (team,)
        )

        row = await cursor.fetchone()

        if not row:
            await interaction.response.send_message(
                "❌ Cette équipe n'existe pas.",
                ephemeral=True
            )
            return

        new_points = row[0] - points

        await db.execute(
            "UPDATE teams SET points = ? WHERE name = ?",
            (new_points, team)
        )

        await db.commit()

    await interaction.response.send_message(
        f"➖ {points} point(s) retiré(s) à {team}\n"
        f"🏆 {team} possède maintenant {new_points} point(s).",
        ephemeral=True
    )
# ==================================
# REPORT RESULT
# ==================================

@bot.tree.command(
    name="report_result",
    description="Déclarer un résultat de match"
)
@app_commands.describe(
    opponent="Adversaire",
    score="2-0, 2-1, 1-2 ou 0-2",
    points="Nombre de points attribués au match",
    my_deck="Ton deck",
    opponent_deck="Deck adverse"
)
async def report_result(
    interaction: discord.Interaction,
    opponent: discord.Member,
    score: str,
    points: int,
    my_deck: str,
    opponent_deck: str = "Inconnu"
):

    valid_scores = ["2-0", "2-1", "1-2", "0-2"]

    if score not in valid_scores:
        await interaction.response.send_message(
            "❌ Score invalide.",
            ephemeral=True
        )
        return

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            "SELECT username, team_name FROM players WHERE discord_id = ?",
            (str(interaction.user.id),)
        )
        player_data = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT username, team_name FROM players WHERE discord_id = ?",
            (str(opponent.id),)
        )
        opponent_data = await cursor.fetchone()

        if not player_data:
            await interaction.response.send_message(
                "❌ Tu n'es pas inscrit.",
                ephemeral=True
            )
            return

        if not opponent_data:
            await interaction.response.send_message(
                "❌ Cet adversaire n'est pas inscrit.",
                ephemeral=True
            )
            return

        await db.execute(
            """
            INSERT INTO matches(
                player_id,
                player_name,
                opponent_id,
                opponent_name,
                player_team,
                opponent_team,
                score,
                points,
                player_deck,
                opponent_deck,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(interaction.user.id),
                player_data[0],
                str(opponent.id),
                opponent_data[0],
                player_data[1],
                opponent_data[1],
                score,
                points,
                my_deck,
                opponent_deck,
                "pending"
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ Résultat enregistré.\n📊 Valeur du match : {points} point(s).",
        ephemeral=True
    )


# ==================================
# PENDING RESULTS
# ==================================

@bot.tree.command(
    name="pending_results",
    description="Voir les résultats en attente"
)
async def pending_results(
    interaction: discord.Interaction
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
            SELECT
                id,
                player_name,
                opponent_name,
                score
            FROM matches
            WHERE status='pending'
            """
        )

        rows = await cursor.fetchall()

    if not rows:

        await interaction.response.send_message(
            "✅ Aucun résultat en attente.",
            ephemeral=True
        )

        return

    msg = "📋 Résultats en attente\n\n"

    for row in rows:

        msg += (
            f"#{row[0]} | "
            f"{row[1]} vs {row[2]} "
            f"({row[3]})\n"
        )

    await interaction.response.send_message(msg)
# ==================================
# APPROVE RESULT
# ==================================

@bot.tree.command(
    name="approve_result",
    description="Valider un résultat"
)
async def approve_result(
    interaction: discord.Interaction,
    match_id: int
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
            SELECT
                id,
                player_team,
                opponent_team,
                score,
                status,
                points
            FROM matches
            WHERE id = ?
            """,
            (match_id,)
        )

        match = await cursor.fetchone()

        if not match:
            await interaction.response.send_message(
                "❌ Match introuvable.",
                ephemeral=True
            )
            return

        if match[4] != "pending":
            await interaction.response.send_message(
                "❌ Match déjà traité.",
                ephemeral=True
            )
            return

        player_team = match[1]
        opponent_team = match[2]
        score = match[3]
        match_points = match[5]

        player_wins = int(score.split("-")[0])
        opponent_wins = int(score.split("-")[1])

        winner_team = player_team
        loser_team = opponent_team

        if opponent_wins > player_wins:
            winner_team = opponent_team
            loser_team = player_team

        await db.execute(
            """
            UPDATE teams
            SET points = points + ?
            WHERE name = ?
            """,
            (match_points, winner_team)
        )

        await db.execute(
            """
            UPDATE teams
            SET points = points - ?
            WHERE name = ?
            """,
            (match_points, loser_team)
        )

        await db.execute(
            """
            UPDATE matches
            SET status='approved'
            WHERE id = ?
            """,
            (match_id,)
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ Match #{match_id} validé.\n"
        f"🏆 {winner_team} gagne {match_points} point(s).\n"
        f"📉 {loser_team} perd {match_points} point(s).",
        ephemeral=True
    )


# ==================================
# REJECT RESULT
# ==================================

@bot.tree.command(
    name="reject_result",
    description="Refuser un résultat"
)
async def reject_result(
    interaction: discord.Interaction,
    match_id: int
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
            UPDATE matches
            SET status='rejected'
            WHERE id = ?
            """,
            (match_id,)
        )

        await db.commit()

    await interaction.response.send_message(
        f"❌ Match #{match_id} refusé.", 
        ephemeral=True
    ) 
@bot.tree.command(
    name="team_info",
    description="Voir les informations d'une équipe"
)

async def team_info(
    interaction: discord.Interaction,
    team: str
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT points
            FROM teams
            WHERE name = ?
            """,
            (team,)
        )

        team_data = await cursor.fetchone()

        if not team_data:

            await interaction.response.send_message(
                "❌ Équipe introuvable.", 
                ephemeral=True
            )

            return

        cursor = await db.execute(
            """
            SELECT username
            FROM players
            WHERE team_name = ?
            """
            ,
            (team,)
        )

        players = await cursor.fetchall()

    msg = (
        f"🏆 {team}\n\n"
        f"Points : {team_data[0]}\n\n"
        f"Membres :\n"
    )

    if players:

        for player in players:

            msg += f"• {player[0]}\n"

    else:

        msg += "Aucun membre"

    await interaction.response.send_message(msg) 
@bot.tree.command(
    name="player_info",
    description="Voir les informations d'un joueur"
)
async def player_info(
    interaction: discord.Interaction,
    player: discord.Member
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT
                username,
                team_name,
                deck
            FROM players
            WHERE discord_id = ?
            """,
            (str(player.id),)
        )

        data = await cursor.fetchone()

        if not data:

            await interaction.response.send_message(
                "❌ Joueur non inscrit.", 
                ephemeral=True
            )

            return

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM matches
            WHERE status='approved'
            AND (
                player_id = ?
                OR opponent_id = ?
            )
            """,
            (
                str(player.id),
                str(player.id)
            )
        )

        matches = await cursor.fetchone()

    msg = (
        f"👤 {data[0]}\n\n"
        f"Équipe : {data[1]}\n"
        f"Matchs joués : {matches[0]}"
        )

    await interaction.response.send_message(msg) 
@bot.tree.command(
    name="match_history",
    description="Voir les matchs validés"
)
async def match_history(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT
                id,
                player_name,
                opponent_name,
                score
            FROM matches
            WHERE status='approved'
            ORDER BY id DESC
            LIMIT 20
            """
        )

        matches = await cursor.fetchall()

    if not matches:

        await interaction.response.send_message(
            "❌ Aucun match validé.", 
            ephemeral=True
        )

        return

    msg = "📜 Historique des matchs\n\n"

    for match in matches:

        msg += (
            f"#{match[0]} "
            f"{match[1]} "
            f"{match[3]} "
            f"{match[2]}\n"
        )

    await interaction.response.send_message(msg)
# ==================================
# END TOURNAMENT
# ==================================

@bot.tree.command(
    name="end_tournament",
    description="Terminer le tournoi"
)
async def end_tournament(
    interaction: discord.Interaction
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
            SELECT
                name,
                points
            FROM teams
            ORDER BY points DESC
            """
        )

        teams = await cursor.fetchall()

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM players
            """
        )

        players_count = await cursor.fetchone()

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM matches
            WHERE status='approved'
            """
        )

        matches_count = await cursor.fetchone()

    msg = "🏆 TOURNOI TERMINÉ\n\n"

    msg += "📊 Classement final\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, team in enumerate(teams):

        medal = ""

        if i < 3:
            medal = medals[i]

        msg += (
            f"{medal} "
            f"{team[0]} - "
            f"{team[1]} pts\n"
        )

    msg += "\n"

    msg += (
        f"👥 Joueurs inscrits : "
        f"{players_count[0]}\n"
    )

    msg += (
        f"🎮 Matchs validés : "
        f"{matches_count[0]}\n"
    )

    await interaction.response.send_message(msg)
# ==================================
# DECK STATS
# ==================================

@bot.tree.command(
    name="deck_stats",
    description="Afficher les decks les plus joués"
)
async def deck_stats(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT player_deck
            FROM matches
            WHERE status='approved'
            """
        )

        player_decks = await cursor.fetchall()

        cursor = await db.execute(
            """
            SELECT opponent_deck
            FROM matches
            WHERE status='approved'
            """
        )

        opponent_decks = await cursor.fetchall()

    deck_count = {}

    total = 0

    for deck in player_decks:

        deck_name = deck[0]

        if not deck_name:
            deck_name = "Autres"

        deck_count[deck_name] = (
            deck_count.get(deck_name, 0) + 1
        )

        total += 1

    for deck in opponent_decks:

        deck_name = deck[0]

        if not deck_name:
            deck_name = "Autres"

        deck_count[deck_name] = (
            deck_count.get(deck_name, 0) + 1
        )

        total += 1

    if total == 0:

        await interaction.response.send_message(
            "❌ Aucune donnée disponible.",
            ephemeral=True
        )

        return

    sorted_decks = sorted(
        deck_count.items(),
        key=lambda x: x[1],
        reverse=True
    )

    msg = "📊 Decks les plus joués\n\n"

    for deck, count in sorted_decks:

        percentage = round(
            (count / total) * 100,
            1
        )

        msg += (
            f"{deck} : "
            f"{percentage}% "
            f"({count})\n"
        )

    await interaction.response.send_message(msg)
# ==================================
# WINRATE STATS
# ==================================

@bot.tree.command(
    name="winrate_stats",
    description="Afficher les winrates des decks"
)
async def winrate_stats(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT
                score,
                player_deck,
                opponent_deck
            FROM matches
            WHERE status='approved'
            """
        )

        matches = await cursor.fetchall()

    if not matches:

        await interaction.response.send_message(
            "❌ Aucun match validé.",
            ephemeral=True
        )

        return

    stats = {}

    for score, player_deck, opponent_deck in matches:

        player_deck = player_deck or "Autres"
        opponent_deck = opponent_deck or "Autres"

        player_wins = int(score.split("-")[0])
        opponent_wins = int(score.split("-")[1])

        if player_deck not in stats:
            stats[player_deck] = {"wins": 0, "games": 0}

        if opponent_deck not in stats:
            stats[opponent_deck] = {"wins": 0, "games": 0}

        stats[player_deck]["games"] += 1
        stats[opponent_deck]["games"] += 1

        if player_wins > opponent_wins:
            stats[player_deck]["wins"] += 1
        else:
            stats[opponent_deck]["wins"] += 1

    msg = "📈 Winrates des decks\n\n"

    ranking = []

    for deck, data in stats.items():

        winrate = round(
            (data["wins"] / data["games"]) * 100,
            1
        )

        ranking.append(
            (
                deck,
                winrate,
                data["games"]
            )
        )

    ranking.sort(
        key=lambda x: x[1],
        reverse=True
    )

    for deck, winrate, games in ranking:

        msg += (
            f"{deck} : "
            f"{winrate}% "
            f"({games} matchs)\n"
        )

    await interaction.response.send_message(msg)
# ==================================
# STAFF PANEL
# ==================================

@bot.tree.command(
    name="staff_panel",
    description="Informations administratives"
)
async def staff_panel(
    interaction: discord.Interaction
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )

        return

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            "SELECT COUNT(*) FROM players"
        )
        players = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM teams"
        )
        teams = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM matches
            WHERE status='approved'
            """
        )
        approved = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM matches
            WHERE status='pending'
            """
        )
        pending = (await cursor.fetchone())[0]

    msg = (
        "📋 Staff Panel\n\n"
        f"👥 Joueurs : {players}\n"
        f"🏆 Équipes : {teams}\n"
        f"✅ Matchs validés : {approved}\n"
        f"⏳ Matchs en attente : {pending}"
    )

    await interaction.response.send_message(msg)
# ==================================
# RESET TOURNAMENT
# ==================================

@bot.tree.command(
    name="reset_tournament",
    description="Réinitialiser le tournoi"
)
async def reset_tournament(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "❌ Réservé aux administrateurs.",
            ephemeral=True
        )

        return

    async with aiosqlite.connect("database.db") as db:

        await db.execute("DELETE FROM players")
        await db.execute("DELETE FROM matches")

        await db.execute(
            """
            UPDATE teams
            SET points = 0
            """
        )

        await db.commit()

    await interaction.response.send_message(
        "♻️ Tournoi réinitialisé.\n"
        "Les équipes officielles ont été conservées."
    ) 

from charts import create_deck_graph
@bot.tree.command(
    name="deck_graph",
    description="Graphique des decks les plus joués"
)
async def deck_graph(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT player_deck
            FROM matches
            WHERE status='approved'
            """
        )

        decks = await cursor.fetchall()

    counts = {}

    for deck in decks:

        deck_name = deck[0] or "Autres"

        counts[deck_name] = (
            counts.get(deck_name, 0) + 1
        )

    if not counts:

        await interaction.response.send_message(
            "❌ Aucune donnée.",
            ephemeral=True
        )

        return

    data = sorted(
        counts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    filename = "deck_graph.png"

    create_deck_graph(
        data,
        filename
    )

    await interaction.response.send_message(
        file=discord.File(filename)
    )
from exporter import export_matches
@bot.tree.command(
    name="export_tournament",
    description="Exporter le tournoi"
)
async def export_tournament(
    interaction: discord.Interaction
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
            SELECT
                player_name,
                opponent_name,
                score,
                player_deck,
                opponent_deck,
                status
            FROM matches
            """
        )

        matches = await cursor.fetchall()

    filename = "tournoi.csv"

    export_matches(
        matches,
        filename
    )

    await interaction.response.send_message(
        file=discord.File(filename)
    )
# ==================================
# SETUP OFFICIAL TEAMS
# ==================================

@bot.tree.command(
    name="setup_teams",
    description="Créer toutes les équipes officielles Ulti-Mate"
)
async def setup_teams(
    interaction: discord.Interaction
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )
        return

    official_teams = [
        "The Hunter",
        "Team Spica",
        "Le Fun",
        "Aristochats",
        "Team Star",
        "Leader",
        "Topdeck Believers",
        "Koura Corp",
        "Majin",
        "L'Alliance du Dragon"
    ]

    added = 0

    async with aiosqlite.connect("database.db") as db:

        for team in official_teams:

            await db.execute(
    """
    INSERT OR IGNORE INTO teams(
        name,
        captain,
        wins,
        losses,
        points
    )
    VALUES (?, '', 0, 0, 0)
    """,
    (team,)
)

            added += 1

        await db.commit()

    await interaction.response.send_message(
        f"🏆 {added} équipes officielles importées.",
        ephemeral=True
    )

@bot.tree.command(
    name="sync_teams",
    description="Synchronise toutes les équipes"
)
async def sync_teams(
    interaction: discord.Interaction
):

    if not is_staff(interaction.user):

        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    teams_synced = 0
    added = 0
    updated = 0

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT team_name, role_id
            FROM team_roles
            """
        )

        configs = await cursor.fetchall()

        for team_name, role_id in configs:

            role = interaction.guild.get_role(
                int(role_id)
            )

            if role is None:
                continue

            teams_synced += 1

            for member in role.members:

                cursor = await db.execute(
                    """
                    SELECT discord_id
                    FROM players
                    WHERE discord_id = ?
                    """,
                    (str(member.id),)
                )

                player = await cursor.fetchone()

                if player:

                    await db.execute(
                        """
                        UPDATE players
                        SET team_name = ?
                        WHERE discord_id = ?
                        """,
                        (
                            team_name,
                            str(member.id)
                        )
                    )

                    updated += 1

                else:

                    await db.execute(
                        """
                        INSERT INTO players(
                            discord_id,
                            username,
                            deck,
                            team_name
                        )
                        VALUES (?, ?, NULL, ?)
                        """,
                        (
                            str(member.id),
                            member.display_name,
                            team_name
                        )
                    )
                
                

                    added += 1

        await db.commit()

    await interaction.followup.send(
        f"✅ Synchronisation terminée\n\n"
        f"🏆 Équipes synchronisées : {teams_synced}\n"
        f"👤 Joueurs ajoutés : {added}\n"
        f"🔄 Joueurs mis à jour : {updated}",
        ephemeral=True
    )
@bot.tree.command(
    name="teams_info",
    description="Affiche toutes les équipes"
)
async def teams_info(
    interaction: discord.Interaction
):

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            """
            SELECT
                name,
                captain,
                wins,
                losses,
                points
            FROM teams
            ORDER BY points DESC
            """
        )

        teams = await cursor.fetchall()

        if not teams:

            await interaction.response.send_message(
                "❌ Aucune équipe trouvée.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🏆 Classement des équipes",
            color=discord.Color.gold()
        )

        for name, captain, wins, losses, points in teams:

            cursor = await db.execute(
                """
                SELECT username
                FROM players
                WHERE team_name = ?
                ORDER BY username
                """,
                (name,)
            )

            members = await cursor.fetchall()

            member_list = "\n".join(
                f"• {member[0]}"
                for member in members
            )

            if not member_list:
                member_list = "Aucun membre"

            embed.add_field(
                name=name,
                value=(
                    f"👑 Capitaine : {captain or 'Non défini'}\n"
                    f"🏅 Points : {points}\n"
                    f"✅ Victoires : {wins}\n"
                    f"❌ Défaites : {losses}\n\n"
                    f"👥 Membres ({len(members)})\n"
                    f"{member_list}"
                ),
                inline=False
            )

    await interaction.response.send_message(
        embed=embed
    )
@bot.tree.command(
    name="setup_team_role",
    description="Associe une équipe à un rôle Discord"
)
@app_commands.autocomplete(equipe=team_autocomplete)
@app_commands.describe(
    equipe="Nom de l'équipe",
    role="Rôle Discord correspondant"
)
async def setup_team_role(
    interaction: discord.Interaction,
    equipe: str,
    role: discord.Role
):

    if not is_staff(interaction.user):
        await interaction.response.send_message(
            "❌ Permission refusée.",
            ephemeral=True
        )
        return

    async with aiosqlite.connect("database.db") as db:

        cursor = await db.execute(
            "SELECT name FROM teams WHERE name = ?",
            (equipe,)
        )

        team = await cursor.fetchone()

        if not team:
            await interaction.response.send_message(
                f"❌ L'équipe **{equipe}** n'existe pas.",
                ephemeral=True
            )
            return

        await db.execute(
            """
            INSERT OR REPLACE INTO team_roles
            (team_name, role_id)
            VALUES (?, ?)
            """,
            (
                equipe,
                str(role.id)
            )
        )

        await db.commit()

    await interaction.response.send_message(
        f"✅ Le rôle **{role.name}** est maintenant lié à **{equipe}**.",
        ephemeral=True
    )
@bot.tree.command(
    name="set_points",
    description="Définir les points d'une équipe"
)
@app_commands.autocomplete(team=team_autocomplete)
async def set_points(
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
            "SELECT 1 FROM teams WHERE name = ?",
            (team,)
        )

        if not await cursor.fetchone():
            await interaction.response.send_message(
                "❌ Cette équipe n'existe pas.",
                ephemeral=True
            )
            return

        await db.execute(
            "UPDATE teams SET points = ? WHERE name = ?",
            (points, team)
        )

        await db.commit()

    await interaction.response.send_message(
        f"🏆 {team} possède maintenant {points} point(s).",
        ephemeral=True
    )

bot.run(TOKEN)

