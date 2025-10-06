from datetime import date
from typing import AsyncGenerator

import polars as pl
import pytest
import pytest_asyncio
from api.config import Settings
from api.data import StockDataDB
from api.models import Interval, Period
from httpx import ASGITransport, AsyncClient
from main import app

settings = Settings()


@pytest_asyncio.fixture(scope="module")
async def nse_stock_data() -> pl.LazyFrame:
    sd = StockDataDB(settings.stockdb.data_base_path / "nse/ticker_history")
    return sd.table_data


@pytest_asyncio.fixture(scope="module")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_ticker_history_tcs(
    async_client: AsyncClient, nse_stock_data: pl.LazyFrame
):
    response = await async_client.get(
        url="/api/per-security/nse/tcs/history",
        params={
            "period": Period.ONE_MONTH.value,
            "interval": Interval.ONE_DAY.value,
        },
    )
    assert response.status_code == 200

    result = pl.LazyFrame(response.json())
    assert result.collect_schema().names() == nse_stock_data.collect_schema().names()
    assert not result.select("close").collect().is_empty()
    count = (
        await result.filter(pl.col("ticker") == "TCS")
        .select("ticker")
        .count()
        .collect_async()
    )
    assert count.item() > 0
    assert count.item() < 31  # less than 31 days in a month


@pytest.mark.asyncio
async def test_ticker_history_tcs_date(
    async_client: AsyncClient, nse_stock_data: pl.LazyFrame
):
    only_date_response = await async_client.get(
        url="/api/per-security/nse/tcs/history",
        params={
            "start_date": date(2024, 3, 10),
            "end_date": date(2024, 3, 20),
        },  # type: ignore
    )
    only_date_result = pl.LazyFrame(only_date_response.json())

    assert only_date_response.status_code == 200

    assert (
        only_date_result.collect_schema().names()
        == nse_stock_data.collect_schema().names()
    )
    assert not only_date_result.select("close").collect().is_empty()

    dates = await only_date_result.select(
        pl.col("date").min().cast(pl.Datetime).cast(pl.Date).alias("min_date"),
        pl.col("date").max().cast(pl.Datetime).cast(pl.Date).alias("max_date"),
    ).collect_async()
    assert dates.item(0, "min_date") >= date(2024, 3, 10)
    assert dates.item(0, "max_date") <= date(2024, 3, 20)

    # 1 month
    dates_and_interval_response = await async_client.get(
        url="/api/per-security/nse/tcs/history",
        params={
            "start_date": date(2024, 3, 1),
            "end_date": date(2024, 5, 30),
            "interval": Interval.ONE_MONTH.value,
        },  # type: ignore
    )
    dates_and_interval_result = pl.LazyFrame(dates_and_interval_response.json())
    assert dates_and_interval_response.status_code == 200
    assert not dates_and_interval_result.select("close").collect().is_empty()
    assert dates_and_interval_result.select("close").count().collect().item() == 3

    # 1 week
    dates_and_interval_response = await async_client.get(
        url="/api/per-security/nse/tcs/history",
        params={
            "start_date": date(2024, 3, 1),
            "end_date": date(2024, 5, 30),
            "interval": Interval.ONE_WEEK.value,
        },  # type: ignore
    )
    dates_and_interval_1w_result = pl.LazyFrame(dates_and_interval_response.json())
    assert dates_and_interval_response.status_code == 200
    assert not dates_and_interval_1w_result.select("close").collect().is_empty()
    assert dates_and_interval_1w_result.select("close").count().collect().item() == 13
