"""The startup schema must match database_setup.sql, which local development uses."""

from pathlib import Path

import asyncpg

from api.schema import SCHEMA_STATEMENTS, apply_schema

SQL_FILE = Path(__file__).resolve().parent.parent / "database_setup.sql"


def normalise(statement: str) -> str:
    return " ".join(statement.split())


def statements_in_sql_file() -> set[str]:
    """CREATE statements from the SQL file, without comments or psql commands."""
    lines = []
    for line in SQL_FILE.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or stripped.startswith("\\"):
            continue
        lines.append(line)
    result = set()
    for piece in " ".join(lines).split(";"):
        text = normalise(piece)
        if text.upper().startswith("CREATE"):
            result.add(text)
    return result


def test_startup_schema_matches_the_sql_file() -> None:
    assert {normalise(s) for s in SCHEMA_STATEMENTS} == statements_in_sql_file()


async def test_schema_can_be_applied_twice(test_database_url: str) -> None:
    pool = await asyncpg.create_pool(test_database_url)
    try:
        await apply_schema(pool)
        await apply_schema(pool)
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT to_regclass('entries') IS NOT NULL")
    finally:
        await pool.close()
