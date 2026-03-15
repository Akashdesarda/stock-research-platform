from dataclasses import dataclass, field

from httpx import AsyncClient

from stocksense.config import get_settings
from stocksense.data import StockDataDB

settings = get_settings()


@dataclass
class CompanyDataContextDependency:
    exchange: str
    ticker: str
    stockdb_api_base_url: str = (
        f"{settings.common.base_url}:{settings.stockdb.port}/api"
    )
    http_client: AsyncClient = field(init=False)

    def __post_init__(self):
        self.http_client = AsyncClient(
            base_url=self.stockdb_api_base_url,
            timeout=None,
        )


@dataclass
class StockDBContextDependency:
    """Context that can be used as dependency injection by the Agent"""

    columns: list[str]
    table_name: str = StockDataDB.table_name
    stockdb_api_base_url: str = (
        f"{settings.common.base_url}:{settings.stockdb.port}/api"
    )
    http_client: AsyncClient = field(init=False)

    def __post_init__(self):
        self.http_client = AsyncClient(
            base_url=self.stockdb_api_base_url,
            timeout=None,
        )
