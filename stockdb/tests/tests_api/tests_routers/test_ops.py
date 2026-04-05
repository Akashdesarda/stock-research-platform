from datetime import date
from typing import AsyncGenerator

import polars as pl
import pytest
import pytest_asyncio
from api.models import DataRegistrationInput, LogicalPlan
from httpx import ASGITransport, AsyncClient
from main import app
from stocksense.config import get_settings
from stocksense.types import DataInterval, DataPeriod

settings = get_settings()


@pytest_asyncio.fixture(scope="module")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_register_data_sql(async_client: AsyncClient):
    data_plain_sql = DataRegistrationInput(
        dataset_id="unit-test-sql-1",
        name="test_data_sql",
        description="Test data registration",
        logical_plan=LogicalPlan(
            exchange="nse",  # type: ignore
            sql_query="SELECT * FROM stockdb WHERE ticker = 'TCS' AND date >= '2024-01-01'",
        ),
        tags=["tcs", "unit company", "sql"],
    )
    response_query = await async_client.put(
        "/api/operation/data/register", json=data_plain_sql.model_dump(mode="json")
    )
    assert response_query.status_code == 201


@pytest.mark.asyncio
async def test_register_data_param(async_client: AsyncClient):
    data_plain_param = DataRegistrationInput(
        dataset_id="unit-test-param-1",
        name="test_data_param",
        description="Test data registration with parameters",
        logical_plan=LogicalPlan(
            exchange="nse",  # type: ignore
            ticker=["TCS", "INFY", "RELIANCE"],
            interval=DataInterval.ONE_DAY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        ),
        tags=["tcs", "unit company", "parameterized"],
    )
    response_param = await async_client.put(
        "/api/operation/data/register", json=data_plain_param.model_dump(mode="json")
    )
    assert response_param.status_code == 201


@pytest.mark.asyncio
async def test_register_data_ai(async_client: AsyncClient):
    data_plain_ai = DataRegistrationInput(
        dataset_id="unit-test-param-ai-1",
        logical_plan=LogicalPlan(
            exchange="nse",  # type: ignore
            ticker=["TCS", "INFY", "RELIANCE"],
            interval=DataInterval.FIVE_DAYS,
            period=DataPeriod.SIX_MONTHS,
        ),
        tags=["tcs", "infy", "unit company", "parameterized"],
    )
    response_param_ai = await async_client.put(
        "/api/operation/data/register", json=data_plain_ai.model_dump(mode="json")
    )
    assert response_param_ai.status_code == 201


@pytest.mark.asyncio
async def test_list_registered_data(async_client: AsyncClient):
    response = await async_client.get("/api/operation/data")
    assert response.status_code == 200

    data = pl.LazyFrame(response.json())
    assert not data.limit(1).collect().is_empty()

    # Validate data
    test = data.filter(pl.col("dataset_id") == "unit-test-sql-1")
    assert not test.collect().is_empty()
    assert (
        test.select(pl.col("logical_plan").struct.field("sql_query")).collect().item()
        == "SELECT * FROM stockdb WHERE ticker = 'TCS' AND date >= '2024-01-01'"
    )


@pytest.mark.asyncio
async def test_get_registered_data(async_client: AsyncClient):
    response = await async_client.get("/api/operation/data/unit-test-sql-1")
    assert response.status_code == 200
    assert response.json()["dataset_id"] == "unit-test-sql-1"


@pytest.mark.asyncio
async def test_get_registered_data_not_found(async_client: AsyncClient):
    response = await async_client.get("/api/operation/data/non-existent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_hydrate_registered_data(async_client: AsyncClient):
    logical_plan = LogicalPlan(
        exchange="nse",  # type: ignore
        sql_query="SELECT * FROM stockdb WHERE ticker = 'TCS' LIMIT 5",
    )
    response = await async_client.post(
        "/api/operation/data/hydrate", json=logical_plan.model_dump(mode="json")
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_cache_prompt_response(async_client: AsyncClient):
    cache_data = {
        "prompt": "What is the PE ratio of TCS?",
        "response": "The PE ratio of TCS is around 30.",
        "thinking": "Retrieving financial data for TCS...",
        "agent": "fundamental-analyst",
        "model": "gemini-pro",
        "ttl": 7,
    }
    response = await async_client.put("/api/operation/prompt/cache", json=cache_data)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_search_prompt_cache(async_client: AsyncClient):
    search_data = {
        "prompt": "What is the PE ratio of TCS?",
        "agent": "fundamental-analyst",
    }
    response = await async_client.post("/api/operation/prompt/search", json=search_data)
    assert response.status_code == 200
    assert response.json()["response"] == "The PE ratio of TCS is around 30."


@pytest.mark.asyncio
async def test_search_prompt_cache_not_found(async_client: AsyncClient):
    search_data = {
        "prompt": "What is the PE ratio of an unknown company?",
        "agent": "fundamental-analyst",
    }
    response = await async_client.post("/api/operation/prompt/search", json=search_data)
    assert response.status_code == 404
