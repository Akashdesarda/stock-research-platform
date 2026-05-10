from stocksense.strategy.catalog import (
    CatalogCategory,
    MarketRegime,
    TimeHorizon,
    list_catalog,
    list_strategies,
)
from stocksense.strategy.catalog.registry import (
    StrategyRegistry,
    build_registry,
    filter_strategies,
    get_registry,
    list_strategies_by_parent,
)


def test_build_registry_compiles_catalogs_and_indexes():
    registry = build_registry()

    assert isinstance(registry, StrategyRegistry)
    assert registry.catalogs == list_catalog()
    assert registry.strategies == tuple(list_strategies())
    assert registry.by_parent
    assert registry.by_id
    assert registry.by_category
    assert registry.by_tag
    assert registry.by_market_regime
    assert registry.by_time_horizon
    assert registry.by_required_column


def test_build_registry_indexes_catalogs_by_parent():
    registry = build_registry()

    for parent, catalogs in registry.by_parent.items():
        assert all(catalog.parent.value == parent for catalog in catalogs)

    assert set(registry.by_parent) == {
        catalog.parent.value for catalog in registry.catalogs
    }
    assert "technical analysis" in registry.by_parent


def test_build_registry_indexes_strategies_by_id_and_category():
    registry = build_registry()

    for strategy in registry.strategies:
        assert registry.by_id[strategy.id] == strategy

    for category, strategies in registry.by_category.items():
        assert all(strategy.category == category for strategy in strategies)

    assert set(registry.by_category) == {
        strategy.category for strategy in registry.strategies
    }
    assert CatalogCategory.trend in registry.by_category


def test_build_registry_indexes_strategies_by_tag_regime_horizon_and_column():
    registry = build_registry()

    for tag, strategies in registry.by_tag.items():
        assert all(tag in strategy.tags for strategy in strategies)

    for market_regime, strategies in registry.by_market_regime.items():
        assert all(market_regime in strategy.market_regimes for strategy in strategies)

    for time_horizon, strategies in registry.by_time_horizon.items():
        assert all(time_horizon in strategy.time_horizons for strategy in strategies)

    for required_column, strategies in registry.by_required_column.items():
        assert all(
            required_column in strategy.required_columns for strategy in strategies
        )

    assert "momentum" in registry.by_tag
    assert MarketRegime.trending in registry.by_market_regime
    assert TimeHorizon.swing in registry.by_time_horizon
    assert "close" in registry.by_required_column


def test_get_registry_returns_cached_registry_instance():
    first_registry = get_registry()
    second_registry = get_registry()

    assert first_registry is second_registry


def test_list_strategies_by_parent_returns_matching_strategies():
    strategies = list_strategies_by_parent("technical analysis")

    assert strategies
    assert strategies == tuple(list_strategies())


def test_filter_strategies_returns_intersection_of_registry_indexes():
    strategies = filter_strategies(
        parent="technical analysis",
        category=CatalogCategory.momentum,
        tags=["volume-confirmation"],
        market_regimes=[MarketRegime.trending],
        time_horizons=[TimeHorizon.swing],
        required_columns=["volume"],
    )

    assert strategies
    assert [strategy.id for strategy in strategies] == ["momentum.mfi"]
