from datetime import date
from typing import AsyncGenerator

import polars as pl
import pytest
import pytest_asyncio
from api.models import Interval, Period
from httpx import ASGITransport, AsyncClient
from main import app
from stocksense.config import get_settings
from stocksense.data import StockDataDB

settings = get_settings(os.getenv("CONFIG_FILE"))


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


@pytest.mark.asyncio
async def test_ticker_query_simple(async_client: AsyncClient):
    simple_query1 = "select * from self where ticker = 'TCS' limit 5"
    query_response = await async_client.post(
        url="/api/per-security/nse/query",
        json={"sql_query": simple_query1},
    )
    query_result = pl.LazyFrame(query_response.json())

    assert query_response.status_code == 200
    assert query_result.select("ticker").unique().collect().item() == "TCS"
    assert query_result.select("ticker").count().collect().item() == 5

    simple_query2 = (
        "select date, ticker, open, close from self "
        "where ticker = 'TCS' and date between '2024-03-01' and '2024-03-10'"
    )
    query_response = await async_client.post(
        url="/api/per-security/nse/query",
        json={"sql_query": simple_query2},
    )
    query_result = pl.LazyFrame(query_response.json())
    assert query_response.status_code == 200
    assert query_result.select("ticker").unique().collect().item() == "TCS"
    dates = await query_result.select(
        pl.col("date").min().cast(pl.Datetime).cast(pl.Date).alias("min_date"),
        pl.col("date").max().cast(pl.Datetime).cast(pl.Date).alias("max_date"),
    ).collect_async()
    assert dates.item(0, "min_date") >= date(2024, 3, 1)
    assert dates.item(0, "max_date") <= date(2024, 3, 10)

    simple_query3 = (
        "select company, max(close) from self "
        "group by company order by close desc limit 5"
    )
    query_response = await async_client.post(
        url="/api/per-security/nse/query",
        json={"sql_query": simple_query3},
    )
    query_result = pl.LazyFrame(query_response.json())
    assert query_response.status_code == 200
    assert query_result.select("company").count().collect().item() == 5
    assert (
        "MRF Limited" in query_result.select("company").collect().to_series().to_list()
    )


@pytest.mark.asyncio
async def test_ticker_query_complex(async_client: AsyncClient):
    complex_query = (
        "select ticker, avg(close) as avg_close, max(high) as max_high "
        "from self where date between '2024-01-01' and '2024-06-01' "
        "group by ticker having avg_close > 3000 "
        "order by avg_close desc limit 3"
    )
    query_response = await async_client.post(
        url="/api/per-security/nse/query",
        json={"sql_query": complex_query},
    )
    query_result = pl.LazyFrame(query_response.json())
    assert query_response.status_code == 200
    assert query_result.select("ticker").count().collect().item() == 3
    avg_closes = await query_result.select("avg_close").collect_async()
    for i in range(avg_closes.height):
        assert avg_closes.item(i, "avg_close") > 3000

    complex_query_2 = (
        "select ticker, sum(volume) as total_volume "
        "from self where date between '2024-05-01' and '2024-05-31' "
        "group by ticker order by total_volume desc limit 5"
    )
    query_response = await async_client.post(
        url="/api/per-security/nse/query",
        json={"sql_query": complex_query_2},
    )
    query_result = pl.LazyFrame(query_response.json())
    assert query_response.status_code == 200
    assert query_result.select("ticker").count().collect().item() == 5
