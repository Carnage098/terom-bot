import aiosqlite

DB_NAME = "database.db"

async def init_db():

async with aiosqlite.connect(DB_NAME) as db:

    # ==================================
    # TOURNOIS
    # ==================================

    await db.execute("""
    CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        active INTEGER DEFAULT 1
    )
    """)

    # ==================================
    # ÉQUIPES
    # ==================================

    await db.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT UNIQUE NOT NULL,
        tag TEXT DEFAULT '',
        captain TEXT DEFAULT '',

        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,

        points INTEGER DEFAULT 0
    )
    """)

    # ==================================
    # JOUEURS
    # ==================================

    await db.execute("""
    CREATE TABLE IF NOT EXISTS players (
        discord_id TEXT PRIMARY KEY,

        username TEXT NOT NULL,
        deck TEXT,

        team_name TEXT,

        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,

        FOREIGN KEY(team_name)
        REFERENCES teams(name)
    )
    """)

    # ==================================
    # MATCHS
    # ==================================

    await db.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        player_id TEXT,
        player_name TEXT,

        opponent_id TEXT,
        opponent_name TEXT,

        player_team TEXT,
        opponent_team TEXT,

        score TEXT,

        points INTEGER DEFAULT 1,

        player_deck TEXT,
        opponent_deck TEXT,

        status TEXT DEFAULT 'pending',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==================================
    # ASSOCIATION ROLE -> ÉQUIPE
    # ==================================

    await db.execute("""
    CREATE TABLE IF NOT EXISTS team_roles (
        team_name TEXT PRIMARY KEY,
        role_id TEXT NOT NULL
    )
    """)

    # Ajout de la colonne points pour les anciennes bases
    try:
        await db.execute("""
        ALTER TABLE matches
        ADD COLUMN points INTEGER DEFAULT 1
        """)
    except:
        pass

    await db.commit()

print("✅ Base de données initialisée")