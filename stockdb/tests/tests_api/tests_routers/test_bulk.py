from datetime import date
from typing import AsyncGenerator

import polars as pl
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
from stocksense.config import get_settings

settings = get_settings()


@pytest_asyncio.fixture(scope="module")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_ticker_query_simple(async_client: AsyncClient):
    simple_query1 = "select * from stockdb where ticker = 'TCS' limit 5"
    query_response = await async_client.post(
        url="/api/bulk/query",
        json={"exchange": "nse", "sql_query": simple_query1},
    )

    assert query_response.status_code == 200

    query_result = pl.LazyFrame(query_response.json())
    assert query_result.select("ticker").unique().collect().item() == "TCS"
    assert query_result.select("ticker").count().collect().item() == 5

    simple_query2 = (
        "select date, ticker, open, close from stockdb "
        "where ticker = 'TCS' and date between '2024-03-01' and '2024-03-10'"
    )
    query_response = await async_client.post(
        url="/api/bulk/query",
        json={"exchange": "nse", "sql_query": simple_query2},
    )
    assert query_response.status_code == 200

    query_result = pl.LazyFrame(query_response.json())
    assert query_result.select("ticker").unique().collect().item() == "TCS"
    dates = await query_result.select(
        pl.col("date").min().cast(pl.Datetime).cast(pl.Date).alias("min_date"),
        pl.col("date").max().cast(pl.Datetime).cast(pl.Date).alias("max_date"),
    ).collect_async()
    assert dates.item(0, "min_date") >= date(2024, 3, 1)
    assert dates.item(0, "max_date") <= date(2024, 3, 10)

    simple_query3 = (
        "select company, max(close) as max_close from stockdb "
        "group by company order by max_close desc limit 5"
    )
    query_response = await async_client.post(
        url="/api/bulk/query",
        json={"exchange": "nse", "sql_query": simple_query3},
    )
    assert query_response.status_code == 200

    query_result = pl.LazyFrame(query_response.json())
    assert query_result.select("company").count().collect().item() == 5
    assert (
        "MRF Limited" in query_result.select("company").collect().to_series().to_list()
    )


@pytest.mark.asyncio
async def test_ticker_query_complex(async_client: AsyncClient):
    complex_query = (
        "select ticker, avg(close) as avg_close, max(high) as max_high "
        "from stockdb where date between '2024-01-01' and '2024-06-01' "
        "group by ticker having avg_close > 3000 "
        "order by avg_close desc limit 3"
    )
    query_response = await async_client.post(
        url="/api/bulk/query",
        json={"exchange": "nse", "sql_query": complex_query},
    )
    assert query_response.status_code == 200

    query_result = pl.LazyFrame(query_response.json())
    assert query_result.select("ticker").count().collect().item() == 3
    avg_closes = await query_result.select("avg_close").collect_async()
    for i in range(avg_closes.height):
        assert avg_closes.item(i, "avg_close") > 3000

    complex_query_2 = (
        "select ticker, sum(volume) as total_volume "
        "from stockdb where date between '2024-05-01' and '2024-05-31' "
        "group by ticker order by total_volume desc limit 5"
    )
    query_response = await async_client.post(
        url="/api/bulk/query",
        json={"exchange": "nse", "sql_query": complex_query_2},
    )
    assert query_response.status_code == 200

    query_result = pl.LazyFrame(query_response.json())
    assert query_result.select("ticker").count().collect().item() == 5
