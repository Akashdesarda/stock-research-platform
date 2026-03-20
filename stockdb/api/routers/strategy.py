import logging
from base64 import b64decode

import httpx
import polars as pl
from fastapi import APIRouter, HTTPException, status
from stocksense.config import get_settings
from stocksense.strategy import TechnicalAnalysis, catalog

from api.models import APITags, ApplyStrategyInput, RegisteredDataOutput

logger = logging.getLogger("stockdb")
settings = get_settings()

# SECTION - FastAPI Router and Endpoints
router = APIRouter(prefix="/api/strategy", tags=[APITags.strategy])


@router.get("/")
async def list_strategies() -> list[catalog.StrategyDescriptor]:
    """List every strategies available in all the catalogs"""
    return catalog.list_strategies()


@router.get("/catalog")
async def list_strategies_as_catalog_grouped() -> tuple[catalog.StrategyCatalog, ...]:
    """List all strategies available grouped by catalog"""
    return catalog.list_catalog()


@router.get("/catalog/{category}")
async def list_strategies_by_category(
    category: catalog.CatalogCategory,
) -> list[catalog.StrategyDescriptor]:
    """List all strategies in the catalog that belong to a specific category"""
    return catalog.list_strategies_by_category(category)


@router.get("/id")
async def get_catalog_strategy_id_map() -> dict[catalog.CatalogCategory, list[str]]:
    """Get a mapping of catalog categories to the IDs of strategies that belong to each category"""
    return catalog.get_catalog_strategy_id_map()


@router.get("/id/{strategy_id}")
async def get_strategy_by_id(strategy_id: str) -> catalog.StrategyDescriptor:
    """Get a strategy descriptor by its unique ID"""
    return catalog.get_strategy_by_id(strategy_id)


@router.post("/apply")
async def apply_strategy_to_registered_dataset(input: ApplyStrategyInput) -> list[dict]:
    """Apply a strategy to a registered dataset and get the results"""
    # getting the data
    async with httpx.AsyncClient() as client:
        _ = await client.get(
            f"{settings.common.base_url}:{settings.stockdb.port}/api/operation/data/{input.registered_dataset_id}"
        )
        if _.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get registered dataset with id '{input.registered_dataset_id}'",
            )

        dataset = RegisteredDataOutput.model_validate(_.json())
        logger.info(
            f"using dataset:{dataset.name} last modified: {dataset.last_modified}"
            f" to apply strategy: {input.strategy_id}"
        )

        _ = await client.get(
            f"{settings.common.base_url}:{settings.stockdb.port}/api/operation/data/{input.registered_dataset_id}/serialize"
        )
        logical_plan_bytes = b64decode(_.json())
        data = pl.LazyFrame.deserialize(logical_plan_bytes)
        logger.debug(f"successfully deserialized dataset: {dataset.name}")

    # getting the strategy accessor
    logger.debug(f"applying strategy: {input.strategy_id} to dataset: {dataset.name}")
    strategy_descriptor = catalog.get_strategy_by_id(input.strategy_id)
    accessor, method = strategy_descriptor.id.split(".")
    ta = TechnicalAnalysis(data)
    strategy_method = getattr(ta, accessor)
    strategy_func = getattr(strategy_method, method)
    result = strategy_func(**input.parameters)
    result = await result.collect_async()
    logger.info(
        f"successfully applied strategy: {input.strategy_id} to dataset: {dataset.name}"
    )
    return result.to_dicts()
