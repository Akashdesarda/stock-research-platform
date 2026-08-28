from collections.abc import AsyncGenerator

import polars as pl
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from stocksense.config import get_settings

from main import app

settings = get_settings()


@pytest_asyncio.fixture(scope="module")
async def async_client() -> AsyncGenerator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def registered_dataset_id(async_client: AsyncClient) -> str:
    dataset_id = "unit-test-strategy"
    registration_payload = {
        "dataset_id": dataset_id,
        "name": "test_strategy_dataset",
        "description": "Dataset registered for strategy API tests",
        "logical_plan": {
            "exchange": "nse",
            "sql_query": "SELECT * FROM stockdb WHERE ticker = 'TCS' AND date >= '2024-01-01'",
        },
        "tags": ["tcs", "strategy", "unit-test"],
    }

    response = await async_client.put(
        "/api/operation/data/register", json=registration_payload
    )
    assert response.status_code == 201

    return dataset_id


@pytest.mark.asyncio
async def test_list_strategy(async_client: AsyncClient):
    response = await async_client.get("/api/strategy/")
    assert response.status_code == 200
    strategies = response.json()
    assert isinstance(strategies, list)
    assert len(strategies) > 0


@pytest.mark.asyncio
async def test_list_strategies_as_catalog_grouped(async_client: AsyncClient):
    response = await async_client.get("/api/strategy/catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_strategies_by_category(async_client: AsyncClient):
    response = await async_client.get("/api/strategy/catalog/momentum")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_catalog_strategy_id_map(async_client: AsyncClient):
    response = await async_client.get("/api/strategy/id")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_get_strategy_by_id(async_client: AsyncClient):
    map_response = await async_client.get("/api/strategy/id")
    assert map_response.status_code == 200
    id_map = map_response.json()

    category = list(id_map.keys())[0]
    strategy_id = id_map[category][0]

    response = await async_client.get(f"/api/strategy/id/{strategy_id}")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] == strategy_id


@pytest.mark.asyncio
async def test_apply_strategy_to_registered_dataset(
    async_client: AsyncClient, registered_dataset_id: str
):
    payload = {
        "registered_dataset_id": registered_dataset_id,
        "strategies": [
            {
                "strategy_id": "momentum.rsi",
                "parameters": {"period": 14},
            }
        ],
    }

    response = await async_client.post("/api/strategy/apply", json=payload)

    assert response.status_code == 200

    # checking if data is returned
    data = pl.from_dicts(response.json()).lazy()
    assert not data.limit(1).collect().is_empty()
    assert "RSI_14" in data.collect_schema().names()


@pytest.mark.asyncio
async def test_apply_multiple_strategies_to_registered_dataset(
    async_client: AsyncClient, registered_dataset_id: str
):
    payload = {
        "registered_dataset_id": registered_dataset_id,
        "strategies": [
            {
                "strategy_id": "momentum.rsi",
                "parameters": {"period": 14},
            },
            {
                "strategy_id": "trend.sma_crossover",
                "parameters": {"fast": 10, "slow": 20},
            },
        ],
    }

    response = await async_client.post("/api/strategy/apply", json=payload)

    assert response.status_code == 200

    # checking if data is returned with columns from both strategies
    data = pl.from_dicts(response.json()).lazy()
    assert not data.limit(1).collect().is_empty()
    schema_names = data.collect_schema().names()
    assert "RSI_14" in schema_names
    assert "SMA_10" in schema_names
    assert "SMA_20" in schema_names
    assert "SMA_crossover_10_20" in schema_names


@pytest.mark.asyncio
async def test_apply_strategy_to_nonexistent_registered_dataset(
    async_client: AsyncClient,
):
    payload = {
        "registered_dataset_id": "nonexistent-dataset",
        "strategies": [
            {
                "strategy_id": "momentum.rsi",
                "parameters": {"period": 14},
            }
        ],
    }

    response = await async_client.post("/api/strategy/apply", json=payload)

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"failed to get registered dataset: '{payload['registered_dataset_id']}'"
    )
