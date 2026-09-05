import logging

from fastapi import APIRouter, HTTPException, status
from stocksense.config import get_settings
from stocksense.strategy import catalog

from api.models import (
    APITags,
    ApplyStrategyInput,
    RegisteredDataOutput,
)
from api.routers import _apply_strategy, _logical_plan_to_lf
from api.routers.ops import get_registered_data

logger = logging.getLogger("stockdb")
settings = get_settings()

# SECTION - FastAPI Router and Endpoints
router = APIRouter(prefix="/api/strategy", tags=[APITags.strategy])


@router.get("/")
async def list_strategies() -> list[catalog.StrategyDescriptor]:
    """List every strategies available in all the catalogs"""
    return catalog.list_strategies()


@router.get("/catalog")
async def list_strategies_as_catalog_grouped() -> tuple[
    catalog.StrategyCatalogIndex, ...
]:
    """List all strategies available grouped by catalog"""
    return catalog.list_strategy_catalogs()


@router.get("/catalog/{category}")
async def list_strategies_by_category(
    category: catalog.StrategyCategoryTypes,
) -> list[catalog.StrategyDescriptor]:
    """List all strategies in the catalog that belong to a specific category"""
    return catalog.list_strategies_by_category(category)


@router.get("/id")
async def get_catalog_strategy_id_map() -> dict[
    catalog.StrategyCategoryTypes, list[str]
]:
    """Get a mapping of catalog categories to the IDs of strategies that belong to each category"""
    return catalog.get_strategy_catalog_id_map()


@router.get("/id/{strategy_id}")
async def get_strategy_by_id(strategy_id: str) -> catalog.StrategyDescriptor:
    """Get a strategy descriptor by its unique ID"""
    return catalog.get_strategy_by_id(strategy_id)


@router.post("/apply")
async def apply_strategy_to_registered_dataset(
    input: ApplyStrategyInput,
) -> list[dict]:
    """Apply strategies to a registered dataset and get the results"""
    # getting the data directly via python function call
    try:
        dataset_info = await get_registered_data(input.registered_dataset_id)
        dataset = RegisteredDataOutput.model_validate(dataset_info)
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"failed to get registered dataset: '{input.registered_dataset_id}'",
            ) from e
        raise

    strategy_ids = [strategy.strategy_id for strategy in input.strategies]
    logger.info(
        f"using dataset:{dataset.name} last modified: {dataset.last_modified}"
        f" to apply strategies: {strategy_ids}"
    )

    # getting the data for the dataset by hydrating the logical plan directly
    data = _logical_plan_to_lf(dataset.logical_plan)
    logger.debug(f"successfully hydrated dataset: {dataset.name}")

    for strategy in input.strategies:
        logger.debug(
            f"applying strategy: {strategy.strategy_id} to dataset: {dataset.name}"
        )
        data = _apply_strategy(data, strategy)

    result = await data.collect_async()
    logger.info(
        f"successfully applied strategies: {strategy_ids} to dataset: {dataset.name}"
    )
    return result.to_dicts()
