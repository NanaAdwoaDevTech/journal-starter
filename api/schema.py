"""Create the database schema at startup. Every statement is idempotent."""

import asyncpg

# Fixed key so replicas that start together take turns instead of colliding
SCHEMA_LOCK_ID = 727001

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS entries (
        id VARCHAR PRIMARY KEY,
        data JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_entries_data_gin ON entries USING GIN (data)",
)


async def apply_schema(pool: asyncpg.Pool) -> None:
    """Create the tables and indexes the API needs if they are missing."""
    async with pool.acquire() as conn:
        await conn.execute("SELECT pg_advisory_lock($1)", SCHEMA_LOCK_ID)
        try:
            for statement in SCHEMA_STATEMENTS:
                await conn.execute(statement)
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", SCHEMA_LOCK_ID)
