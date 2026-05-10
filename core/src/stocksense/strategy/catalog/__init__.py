from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

CATALOG_DIR = Path(__file__).resolve().parent


class ParentCatalog(Enum):
    technical_analysis = "technical analysis"
    # fundamental_analysis = "fundamental analysis"
    # sentiment_analysis = "sentiment analysis"
    # machine_learning = "machine learning"
    # alternative_data = "alternative data"


class CatalogCategory(Enum):
    # Technical Analysis Categories
    trend = "trend"
    momentum = "momentum"
    volatility = "volatility"
    volume = "volume"
    overlap = "overlap"
    cycle = "cycle"
    pattern = "pattern"
    stats = "stats"


class MarketRegime(Enum):
    trending = "trending"
    ranging = "ranging"
    breakout = "breakout"
    volatile = "volatile"
    low_volatility = "low volatility"
    high_volume = "high volume"
    low_volume = "low volume"
    reversal_candidate = "reversal candidate"


class TimeHorizon(Enum):
    intraday = "intraday"
    short_term = "short term"
    swing = "swing"
    medium_term = "medium term"
    long_term = "long term"


class StrategyDecisionGuidance(BaseModel):
    """Guidance for making trading decisions based on the strategy's output."""

    use_if: list[str] | None = None
    combine_with: list[str] | None = None


class StrategyDescriptor(BaseModel):
    """A descriptor for a trading strategy, containing metadata and configuration details."""

    # Identify
    id: str
    name: str
    category: CatalogCategory
    # Description
    summary: str
    purpose: list[str]
    best_for: list[str]
    avoid_when: list[str]
    tags: list[str]
    # Implementation
    required_columns: list[str]
    parameters: dict[str, Any]
    output_columns: list[str]
    # Usage & Guidance
    interpretation: str
    market_regimes: list[MarketRegime]
    time_horizons: list[TimeHorizon]
    decision_guidance: StrategyDecisionGuidance
    limitations: list[str]
    llm_hint: str


class StrategyCatalog(BaseModel):
    """A catalog of trading strategies, loaded from YAML files."""

    name: str
    parent: ParentCatalog
    strategies: dict[str, StrategyDescriptor]


def catalog_files() -> list[Path]:
    """Get all YAML files in the catalog directory that hold information about strategies"""

    return list(CATALOG_DIR.glob("*.yaml"))


@lru_cache()
def list_catalog() -> tuple[StrategyCatalog, ...]:
    """List all strategies available in the catalog"""

    descriptors = []
    for file in catalog_files():
        with file.open() as f:
            data = yaml.safe_load(f)
            descriptor = StrategyCatalog.model_validate(data)
            descriptors.append(descriptor)
    return tuple(descriptors)


def list_strategies() -> list[StrategyDescriptor]:
    """List all strategies available in the catalog"""

    catalogs = list_catalog()
    strategies = []
    for catalog in catalogs:
        strategies.extend(catalog.strategies.values())
    return strategies


def list_strategies_by_parent(parent: str | ParentCatalog) -> list[StrategyDescriptor]:
    """List all strategies in the catalog that belong to a specific parent"""
    if isinstance(parent, str):
        normalized_parent = parent.strip().lower()
        try:
            parent = ParentCatalog(normalized_parent)
        except ValueError as exc:
            valid_values = ", ".join(p.value for p in ParentCatalog)
            raise ValueError(
                f"Invalid parent catalog '{parent}'. "
                f"Expected one of: {valid_values}"
            ) from exc

    catalogs = list_catalog()
    strategies = []
    for catalog in catalogs:
        if catalog.parent == parent:
            strategies.extend(catalog.strategies.values())
    return strategies


def list_strategies_by_category(
    category: CatalogCategory | str,
) -> list[StrategyDescriptor]:
    """List all strategies in the catalog that belong to a specific category"""

    if isinstance(category, str):
        category = CatalogCategory(category)

    strategies = list_strategies()
    return [s for s in strategies if s.category == category]


def get_catalog_strategy_id_map() -> dict[CatalogCategory, list[str]]:
    """Get a mapping of catalog categories to the IDs of strategies that belong to each category"""

    catalogs = list_catalog()
    category_map: dict[CatalogCategory, list[str]] = {}
    for catalog in catalogs:
        for strategy in catalog.strategies.values():
            category_map.setdefault(strategy.category, []).append(strategy.id)
    return category_map


def get_strategy_by_id(strategy_id: str) -> StrategyDescriptor:
    """Get a strategy descriptor by its unique ID"""

    strategies = list_strategies()
    for strategy in strategies:
        if strategy.id == strategy_id:
            return strategy
    raise ValueError(f"Strategy with id '{strategy_id}' not found in catalog")
