from collections.abc import AsyncGenerator

import polars as pl
import polars.selectors as cs
import pytest
import pytest_asyncio
from api.models import LogicalPlan, StrategyApplication
from api.routers import _apply_strategy, _logical_plan_to_lf
from httpx import ASGITransport, AsyncClient
from main import app
from stocksense.config import get_settings
from stocksense.strategy import TechnicalAnalysis

settings = get_settings()

MULTI_TICKER_SQL_QUERY = (
    "SELECT * FROM stockdb WHERE ticker IN ('TCS', 'INFY') AND date >= '2024-01-01'"
)
MULTI_STRATEGY_PAYLOAD = [
    {
        "strategy_id": "momentum.rsi",
        "parameters": {"period": 14},
    },
    {
        "strategy_id": "trend.sma_crossover",
        "parameters": {"fast": 10, "slow": 20},
    },
]
STRATEGY_OUTPUT_COLS = ["RSI_14", "SMA_10", "SMA_20", "SMA_crossover_10_20"]


def _normalize_strategy_output(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(cs.float().fill_nan(None))


def _apply_strategies_like_router(
    data: pl.DataFrame,
    strategies: list[dict],
    *,
    group_by: str | None,
) -> pl.DataFrame:
    analysis = TechnicalAnalysis(data, group_by=group_by, sort_by="date")
    result = data
    for strategy in strategies:
        result = _apply_strategy(
            analysis,
            StrategyApplication(**strategy),
        )
    return result


def _assert_ticker_strategy_values_match_single_ticker_run(
    grouped_result: pl.DataFrame,
    source_data: pl.DataFrame,
    ticker: str,
    strategies: list[dict],
    output_cols: list[str],
) -> None:
    single_ticker_result = _apply_strategies_like_router(
        source_data.filter(pl.col("ticker") == ticker),
        strategies,
        group_by=None,
    )
    grouped = (
        grouped_result
        .filter(pl.col("ticker") == ticker)
        .sort("date")
        .select(output_cols)
    )
    single = single_ticker_result.sort("date").select(output_cols)

    assert (
        _normalize_strategy_output(grouped).to_dicts()
        == _normalize_strategy_output(single).to_dicts()
    )


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
async def test_apply_multiple_strategies_resets_per_ticker(
    async_client: AsyncClient,
):
    dataset_id = "unit-test-strategy-multi-ticker"
    registration_payload = {
        "dataset_id": dataset_id,
        "name": "test_strategy_multi_ticker_dataset",
        "description": "Multi-ticker dataset for per-ticker strategy API tests",
        "logical_plan": {
            "exchange": "nse",
            "sql_query": MULTI_TICKER_SQL_QUERY,
        },
        "tags": ["tcs", "infy", "strategy", "unit-test"],
    }

    register_response = await async_client.put(
        "/api/operation/data/register", json=registration_payload
    )
    assert register_response.status_code == 201

    payload = {
        "registered_dataset_id": dataset_id,
        "strategies": MULTI_STRATEGY_PAYLOAD,
    }
    response = await async_client.post("/api/strategy/apply", json=payload)
    assert response.status_code == 200

    api_result = pl.from_dicts(response.json())
    assert set(api_result["ticker"].unique()) == {"TCS", "INFY"}

    source_data = _logical_plan_to_lf(
        LogicalPlan(exchange="nse", sql_query=MULTI_TICKER_SQL_QUERY)
    ).collect()

    for ticker in ("TCS", "INFY"):
        _assert_ticker_strategy_values_match_single_ticker_run(
            api_result,
            source_data,
            ticker,
            MULTI_STRATEGY_PAYLOAD,
            STRATEGY_OUTPUT_COLS,
        )


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
