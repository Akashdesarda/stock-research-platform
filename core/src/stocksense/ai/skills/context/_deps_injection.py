from dataclasses import dataclass, field

import polars as pl
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
    """Context that can be used as dependency injection by the Agent

    Attributes
    ----------
    history_data: pl.LazyFrame
        The historical stock data for the given exchange and ticker.
    table_name: str
        The name of the table in the StockDataDB, defaults to StockDataDB.table_name
    stockdb_api_base_url: str
        The base URL for the StockDB API, defaults to f"{settings.common.base_url}:{settings.stockdb.port}/api"
    http_client: AsyncClient
        An instance of httpx.AsyncClient for making API requests to the StockDB API.
    """

    history_data: pl.LazyFrame
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
        self.columns = self.history_data.collect_schema().names()
