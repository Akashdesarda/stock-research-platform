import logging
import shutil
from pathlib import Path
from urllib.parse import quote_plus

from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from stocksense.config import get_settings

from ._llm_helper import get_model

logger = logging.getLogger("stocksense")
settings = get_settings()

# Workspace-local fallback when the configured sqlite path is not writable
# (e.g. root-owned file, or a process sandboxed away from ~/.local/share).
_SQLITE_FALLBACK = (
    Path(__file__).resolve().parents[2] / ".data" / "sqlite" / "agno.db"
)


def _path_is_writable(path: Path) -> bool:
    """Return True if we can create/append under this sqlite file path."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            with path.open("a"):
                pass
        else:
            path.touch()
            path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def resolve_sqlite_db_file(configured: str) -> str:
    """Resolve sqlite_path to a writable file, falling back into stocksense-ai/.data.

    AgentOS session continue/rename require durable writes. If the configured
    path cannot be written, copy any existing readable DB into a workspace
    fallback so history is preserved when possible.
    """
    preferred = Path(configured).expanduser()
    if _path_is_writable(preferred):
        return preferred.resolve().as_posix()

    fallback = _SQLITE_FALLBACK
    fallback.parent.mkdir(parents=True, exist_ok=True)
    if preferred.exists() and preferred.is_file() and not fallback.exists():
        try:
            shutil.copy2(preferred, fallback)
            logger.warning(
                "Configured sqlite path is not writable (%s); "
                "copied DB to fallback %s",
                preferred,
                fallback,
            )
        except OSError as e:
            logger.warning(
                "Configured sqlite path is not writable (%s) and copy failed "
                "(%s); using empty fallback %s",
                preferred,
                e,
                fallback,
            )
    else:
        logger.warning(
            "Configured sqlite path is not writable (%s); using fallback %s",
            preferred,
            fallback,
        )

    if not _path_is_writable(fallback):
        raise RuntimeError(
            f"SQLite database is not writable at configured path {preferred} "
            f"or fallback {fallback}. Fix permissions on sqlite_path."
        )
    return fallback.resolve().as_posix()


_SQLITE_DB_FILE = resolve_sqlite_db_file(settings.common.sqlite_path)

postgres_db = PostgresDb(
    db_url=f"postgresql+psycopg://stocksense:{quote_plus(settings.common.postgres_passwd)}@{settings.common.postgres_url}:5432/agno",
    id="traces",
)
async_postgres_db = AsyncPostgresDb(
    db_url=f"postgresql+psycopg_async://stocksense:{quote_plus(settings.common.postgres_passwd)}@{settings.common.postgres_url}:5432/agno",
    id="traces",
)

sqlite_db = SqliteDb(db_file=_SQLITE_DB_FILE, id="stocksense")
async_sqlite_db = AsyncSqliteDb(db_file=_SQLITE_DB_FILE, id="stocksense")

__all__ = [
    "get_model",
    "postgres_db",
    "async_postgres_db",
    "sqlite_db",
    "async_sqlite_db",
    "resolve_sqlite_db_file",
]
