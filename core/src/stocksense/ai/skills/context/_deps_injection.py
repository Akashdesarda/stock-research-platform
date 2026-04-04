from dataclasses import dataclass, field
from datetime import date

import polars as pl
from httpx import AsyncClient

from stocksense.config import get_settings
from stocksense.data import StockDataDB
from stocksense.types import DataInterval, DataPeriod

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


@dataclass
class DatasetDescriptionContextDependency:
    """Context that can be used as dependency injection by the Agent"""

    exchange: str
    ticker_identifier: str | None = None
    interval: DataInterval | None = None
    period: DataPeriod | None = None
    start_date: date | None = None
    end_date: date | None = None
    sql_query: str | None = None

    def as_dict(self):
        return {
            "exchange": self.exchange,
            "ticker_identifier": self.ticker_identifier,
            "interval": self.interval.value if self.interval else None,
            "period": self.period.value if self.period else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "sql_query": self.sql_query,
        }
