from dataclasses import dataclass
from functools import lru_cache

from . import (
    StrategyCategoryTypes,
    MarketRegime,
    AnalysisDomainTypes,
    StrategyCatalogIndex,
    StrategyDescriptor,
    TimeHorizon,
    list_analysis_domains,
    list_strategy_catalogs,
    list_strategies,
    AnalysisDomainIndex,
)


@dataclass(frozen=True)
class StrategyRegistry:
    """Compiled runtime view of the strategy catalog."""

    domains: AnalysisDomainIndex
    strategy_catalogs: tuple[StrategyCatalogIndex, ...]
    strategies: tuple[StrategyDescriptor, ...]
    by_domain: dict[AnalysisDomainTypes, tuple[StrategyCatalogIndex, ...]]
    by_strategy_category: dict[StrategyCategoryTypes, tuple[StrategyDescriptor, ...]]
    by_id: dict[str, StrategyDescriptor]
    by_tag: dict[str, tuple[StrategyDescriptor, ...]]
    by_market_regime: dict[MarketRegime, tuple[StrategyDescriptor, ...]]
    by_time_horizon: dict[TimeHorizon, tuple[StrategyDescriptor, ...]]
    by_required_column: dict[str, tuple[StrategyDescriptor, ...]]


def build_registry() -> StrategyRegistry:
    """Build a compiled registry from the loaded strategy catalogs."""

    domains = list_analysis_domains()
    catalogs = tuple(list_strategy_catalogs())
    strategies = tuple(list_strategies())
    by_domain_lists: dict[AnalysisDomainTypes, list[StrategyCatalogIndex]] = {}
    for catalog in catalogs:
        by_domain_lists.setdefault(catalog.domain, []).append(catalog)

    by_domain_index = {
        domain: tuple(domain_catalogs)
        for domain, domain_catalogs in by_domain_lists.items()
    }

    by_id = {strategy.id: strategy for strategy in strategies}

    by_category_lists: dict[StrategyCategoryTypes, list[StrategyDescriptor]] = {}
    for strategy in strategies:
        by_category_lists.setdefault(strategy.category, []).append(strategy)

    by_category = {
        category: tuple(category_strategies)
        for category, category_strategies in by_category_lists.items()
    }

    by_tag_lists: dict[str, list[StrategyDescriptor]] = {}
    by_market_regime_lists: dict[MarketRegime, list[StrategyDescriptor]] = {}
    by_time_horizon_lists: dict[TimeHorizon, list[StrategyDescriptor]] = {}
    by_required_column_lists: dict[str, list[StrategyDescriptor]] = {}
    for strategy in strategies:
        for tag in strategy.tags:
            by_tag_lists.setdefault(tag, []).append(strategy)
        for market_regime in strategy.market_regimes:
            by_market_regime_lists.setdefault(market_regime, []).append(strategy)
        for time_horizon in strategy.time_horizons:
            by_time_horizon_lists.setdefault(time_horizon, []).append(strategy)
        for required_column in strategy.required_columns:
            by_required_column_lists.setdefault(required_column, []).append(strategy)

    by_tag = {
        tag: tuple(tag_strategies) for tag, tag_strategies in by_tag_lists.items()
    }
    by_market_regime = {
        market_regime: tuple(regime_strategies)
        for market_regime, regime_strategies in by_market_regime_lists.items()
    }
    by_time_horizon = {
        time_horizon: tuple(horizon_strategies)
        for time_horizon, horizon_strategies in by_time_horizon_lists.items()
    }
    by_required_column = {
        required_column: tuple(column_strategies)
        for required_column, column_strategies in by_required_column_lists.items()
    }

    return StrategyRegistry(
        domains=domains,
        strategy_catalogs=catalogs,
        strategies=strategies,
        by_domain=by_domain_index,
        by_id=by_id,
        by_strategy_category=by_category,
        by_tag=by_tag,
        by_market_regime=by_market_regime,
        by_time_horizon=by_time_horizon,
        by_required_column=by_required_column,
    )


@lru_cache()
def get_registry() -> StrategyRegistry:
    """Get the cached compiled strategy registry."""

    return build_registry()


def filter_strategies(
    *,
    domain: AnalysisDomainTypes | str | None = None,
    category: StrategyCategoryTypes | str | None = None,
    tags: list[str] | None = None,
    market_regimes: list[MarketRegime | str] | None = None,
    time_horizons: list[TimeHorizon | str] | None = None,
    required_columns: list[str] | None = None,
) -> tuple[StrategyDescriptor, ...]:
    """Filter strategies using the compiled registry indexes."""

    registry = get_registry()
    strategies: tuple[StrategyDescriptor, ...] = registry.strategies

    if domain is not None:
        if isinstance(domain, str):
            domain = AnalysisDomainTypes(domain.strip().lower())
        domain_catalogs = registry.by_domain.get(domain, ())
        domain_strategy_ids = {
            strategy.id
            for catalog in domain_catalogs
            for strategy in catalog.strategies.values()
        }
        strategies = tuple(
            strategy for strategy in strategies if strategy.id in domain_strategy_ids
        )

    if category is not None:
        if isinstance(category, str):
            category = StrategyCategoryTypes(category.strip().lower())
        category_strategy_ids = {
            strategy.id for strategy in registry.by_strategy_category.get(category, ())
        }
        strategies = tuple(
            strategy for strategy in strategies if strategy.id in category_strategy_ids
        )

    if tags is not None:
        for tag in tags:
            tag_strategy_ids = {
                strategy.id for strategy in registry.by_tag.get(tag, ())
            }
            strategies = tuple(
                strategy for strategy in strategies if strategy.id in tag_strategy_ids
            )

    if market_regimes is not None:
        for market_regime in market_regimes:
            if isinstance(market_regime, str):
                market_regime = MarketRegime(market_regime)
            regime_strategy_ids = {
                strategy.id
                for strategy in registry.by_market_regime.get(market_regime, ())
            }
            strategies = tuple(
                strategy
                for strategy in strategies
                if strategy.id in regime_strategy_ids
            )

    if time_horizons is not None:
        for time_horizon in time_horizons:
            if isinstance(time_horizon, str):
                time_horizon = TimeHorizon(time_horizon)
            horizon_strategy_ids = {
                strategy.id
                for strategy in registry.by_time_horizon.get(time_horizon, ())
            }
            strategies = tuple(
                strategy
                for strategy in strategies
                if strategy.id in horizon_strategy_ids
            )

    if required_columns is not None:
        for required_column in required_columns:
            column_strategy_ids = {
                strategy.id
                for strategy in registry.by_required_column.get(required_column, ())
            }
            strategies = tuple(
                strategy
                for strategy in strategies
                if strategy.id in column_strategy_ids
            )

    return strategies
