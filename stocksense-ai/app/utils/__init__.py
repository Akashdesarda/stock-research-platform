from pathlib import Path
from urllib.parse import quote_plus

from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from stocksense.config import get_settings

from ._llm_helper import get_model

settings = get_settings()

postgres_db = PostgresDb(
    db_url=f"postgresql+psycopg://stocksense:{quote_plus(settings.common.postgres_passwd)}@{settings.common.postgres_url}:5432/agno",
    id="traces",
)
async_postgres_db = AsyncPostgresDb(
    db_url=f"postgresql+psycopg_async://stocksense:{quote_plus(settings.common.postgres_passwd)}@{settings.common.postgres_url}:5432/agno",
    id="traces",
)

sqlite_db = SqliteDb(
    db_file=Path(settings.common.sqlite_path).expanduser().as_posix(), id="stocksense"
)
async_sqlite_db = AsyncSqliteDb(
    db_file=Path(settings.common.sqlite_path).expanduser().as_posix(), id="stocksense"
)

__all__ = [
    "get_model",
    "postgres_db",
    "async_postgres_db",
    "sqlite_db",
    "async_sqlite_db",
]
