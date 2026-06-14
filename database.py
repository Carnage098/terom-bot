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

            guild_id TEXT NOT NULL,

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

            guild_id TEXT NOT NULL,

            name TEXT NOT NULL,
            tag TEXT DEFAULT '',
            captain TEXT DEFAULT '',

            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,

            points INTEGER DEFAULT 0,

            UNIQUE(guild_id, name)
        )
        """)

        # ==================================
        # JOUEURS
        # ==================================

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            discord_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,

            username TEXT NOT NULL,
            deck TEXT,

            team_name TEXT,

            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,

            PRIMARY KEY(discord_id, guild_id)
        )
        """)

        # ==================================
        # MATCHS
        # ==================================

        await db.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            guild_id TEXT NOT NULL,

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
            guild_id TEXT NOT NULL,

            team_name TEXT NOT NULL,
            role_id TEXT NOT NULL,

            PRIMARY KEY(guild_id, team_name)
        )
        """)

        await db.commit()

    print("✅ Base de données initialisée")
