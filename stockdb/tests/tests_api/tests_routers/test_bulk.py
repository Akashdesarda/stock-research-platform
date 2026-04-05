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
        url="/api/bulk/ticker/query",
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
        url="/api/bulk/ticker/query",
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
        url="/api/bulk/ticker/query",
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
        url="/api/bulk/ticker/query",
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
        url="/api/bulk/ticker/query",
        json={"exchange": "nse", "sql_query": complex_query_2},
    )
    assert query_response.status_code == 200

    query_result = pl.LazyFrame(query_response.json())
    assert query_result.select("ticker").count().collect().item() == 5


@pytest.mark.asyncio
async def test_list_tickers(async_client: AsyncClient):
    response = await async_client.get("/api/bulk/list-tickers")
    assert response.status_code == 200
    data = response.json()
    assert "nse" in data
    assert isinstance(data["nse"], list) or data["nse"] is None


@pytest.mark.asyncio
async def test_list_indexes(async_client: AsyncClient):
    response = await async_client.get("/api/bulk/list-indexes")
    assert response.status_code == 200
    data = response.json()
    assert "nse" in data
    assert isinstance(data["nse"], list) or data["nse"] is None


@pytest.mark.asyncio
async def test_ticker_history_period(async_client: AsyncClient):
    input_body = {
        "exchange": "nse",
        "ticker": ["TCS", "INFY"],
        "period": "1mo",
    }
    response = await async_client.post(url="/api/bulk/ticker/history", json=input_body)
    assert response.status_code == 200

    result = pl.LazyFrame(response.json())
    tickers = await result.select("ticker").unique().collect_async()
    assert set(tickers.to_series().to_list()) == {"TCS", "INFY"}

    tcs = await result.filter(pl.col("ticker") == "TCS").collect_async()
    assert tcs.is_empty() is False

    infy = await result.filter(pl.col("ticker") == "INFY").collect_async()
    assert infy.is_empty() is False


@pytest.mark.asyncio
async def test_ticker_history_date_range(async_client: AsyncClient):
    input_body = {
        "exchange": "nse",
        "ticker": ["TCS", "INFY"],
        "start_date": "2025-03-01",
        "end_date": "2025-03-10",
    }
    response = await async_client.post(url="/api/bulk/ticker/history", json=input_body)
    assert response.status_code == 200

    result = pl.LazyFrame(response.json())
    tickers = await result.select("ticker").unique().collect_async()
    assert set(tickers.to_series().to_list()) == {"TCS", "INFY"}

    dates = (
        await result.group_by("ticker")
        .agg(
            pl.len().alias("row_count"),
            pl.col("date").min().cast(pl.Datetime).cast(pl.Date).alias("min_date"),
            pl.col("date").max().cast(pl.Datetime).cast(pl.Date).alias("max_date"),
        )
        .collect_async()
    )

    assert dates.height == 2
    for row in dates.iter_rows(named=True):
        assert row["ticker"] in {"TCS", "INFY"}
        assert row["row_count"] > 0
        assert row["min_date"] >= date.fromisoformat(input_body["start_date"])
        assert row["max_date"] <= date.fromisoformat(input_body["end_date"])
