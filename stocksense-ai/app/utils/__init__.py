from agno.db.postgres import AsyncPostgresDb, PostgresDb
from stocksense.config import get_settings

from ._llm_helper import get_model

settings = get_settings()
from urllib.parse import quote_plus

postgres_db = PostgresDb(
    db_url=f"postgresql+psycopg://stocksense:{quote_plus(settings.common.postgres_passwd)}@{settings.common.postgres_url}:5432/agno",
    id="traces",
)
async_postgres_db = AsyncPostgresDb(
    db_url=f"postgresql+psycopg_async://stocksense:{quote_plus(settings.common.postgres_passwd)}@{settings.common.postgres_url}:5432/agno",
    id="traces",
)

__all__ = ["get_model", "postgres_db", "async_postgres_db"]
