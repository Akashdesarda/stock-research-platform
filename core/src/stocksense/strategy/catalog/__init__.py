from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

CATALOG_DIR = Path(__file__).resolve().parent


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


# SECTION - 1. Analysis Domain Catalog
class AnalysisDomainTypes(Enum):
    technical_analysis = "technical analysis"
    # fundamental_analysis = "fundamental analysis"
    # sentiment_analysis = "sentiment analysis"
    # machine_learning = "machine learning"
    # alternative_data = "alternative data"


class AnalysisDomainCategoryDescriptor(BaseModel):
    """Metadata for a child category under a analysis domain."""

    summary: str
    use_if: list[str]
    example_queries: list[str] | None = None


class AnalysisDomainDescriptor(BaseModel):
    """A descriptor for a Analysis Domain catalog, containing metadata and configuration details."""

    id: AnalysisDomainTypes
    summary: str
    use_if: list[str]
    avoid_when: list[str]
    categories: dict[str, AnalysisDomainCategoryDescriptor]


class AnalysisDomainIndex(BaseModel):
    """Top-level analysis domain index."""

    name: str
    domains: dict[str, AnalysisDomainDescriptor]


# SECTION - 2. Strategy Catalog
class StrategyCategoryTypes(Enum):
    # Technical Analysis Categories
    trend = "trend"
    momentum = "momentum"
    volatility = "volatility"
    volume = "volume"
    overlap = "overlap"
    cycle = "cycle"
    pattern = "pattern"
    stats = "stats"


class StrategyDecisionGuidance(BaseModel):
    """Guidance for making trading decisions based on the strategy's output."""

    use_if: list[str] | None = None
    combine_with: list[str] | None = None


class StrategyDescriptor(BaseModel):
    """A descriptor for a trading strategy, containing metadata and configuration details."""

    # Identify
    id: str
    name: str
    category: StrategyCategoryTypes
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


class StrategyCatalogIndex(BaseModel):
    """A catalog of trading strategies, loaded from YAML files."""

    name: str
    domain: AnalysisDomainTypes
    strategies: dict[str, StrategyDescriptor]


def catalog_files() -> list[Path]:
    """Get all YAML files in the catalog directory that hold information about strategies"""

    return list(CATALOG_DIR.glob("*.yaml"))


def list_analysis_domains() -> AnalysisDomainIndex:
    """List available analysis domains for high-level routing."""
    domain_yaml_path = CATALOG_DIR / "domain.yaml"
    with domain_yaml_path.open() as f:
        data = yaml.safe_load(f)

    return AnalysisDomainIndex.model_validate(data)


def list_strategy_catalogs() -> tuple[StrategyCatalogIndex, ...]:
    """List all strategies available in the catalog"""

    descriptors = []
    for file in catalog_files():
        if file.stem == "domain":
            continue
        with file.open() as f:
            data = yaml.safe_load(f)
            descriptor = StrategyCatalogIndex.model_validate(data)
            descriptors.append(descriptor)
    return tuple(descriptors)


def list_strategies() -> list[StrategyDescriptor]:
    """List all strategies available in the catalog"""

    catalogs = list_strategy_catalogs()
    strategies = []
    for catalog in catalogs:
        strategies.extend(catalog.strategies.values())
    return strategies


def list_strategies_by_domain(
    domain: str | AnalysisDomainTypes,
) -> list[StrategyDescriptor]:
    """List all strategies in the catalog that belong to a specific domain"""
    if isinstance(domain, str):
        normalized_domain = domain.strip().lower()
        try:
            domain = AnalysisDomainTypes(normalized_domain)
        except ValueError as exc:
            valid_values = ", ".join(p.value for p in AnalysisDomainTypes)
            raise ValueError(
                f"Invalid analysis domain '{domain}'. Expected one of: {valid_values}"
            ) from exc

    catalogs = list_strategy_catalogs()
    strategies = []
    for catalog in catalogs:
        if catalog.domain == domain:
            strategies.extend(catalog.strategies.values())
    return strategies


def list_strategies_by_category(
    category: StrategyCategoryTypes | str,
) -> list[StrategyDescriptor]:
    """List all strategies in the catalog that belong to a specific category"""

    if isinstance(category, str):
        category = StrategyCategoryTypes(category)

    strategies = list_strategies()
    return [s for s in strategies if s.category == category]


def get_strategy_catalog_id_map() -> dict[StrategyCategoryTypes, list[str]]:
    """Get a mapping of catalog categories to the IDs of strategies that belong to each category"""

    catalogs = list_strategy_catalogs()
    category_map: dict[StrategyCategoryTypes, list[str]] = {}
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
