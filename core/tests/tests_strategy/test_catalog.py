import pytest
from stocksense.strategy.catalog import (
    StrategyCategoryTypes,
    AnalysisDomainTypes,
    catalog_files,
    get_strategy_catalog_id_map,
    get_strategy_by_id,
    list_analysis_domains,
    list_strategy_catalogs,
    list_strategies,
    list_strategies_by_category,
    list_strategies_by_domain,
)


def test_strategy_catalog_files_exist():
    files = catalog_files()
    assert files


def test_strategy_catalog_loads_all_yaml_files():
    catalogs = list_strategy_catalogs()
    assert len(catalogs) == len(catalog_files()) - 1

    strategies = list_strategies()
    assert strategies
    assert len(strategies) == sum(len(catalog.strategies) for catalog in catalogs)


def test_strategy_catalog_required_fields_are_present():
    for descriptor in list_strategies():
        assert descriptor.id
        assert descriptor.name
        assert descriptor.category
        assert descriptor.summary
        assert descriptor.purpose
        assert descriptor.best_for
        assert descriptor.avoid_when
        assert descriptor.tags
        assert descriptor.required_columns
        assert descriptor.parameters
        assert descriptor.output_columns
        assert descriptor.interpretation
        assert descriptor.market_regimes
        assert descriptor.time_horizons
        assert descriptor.decision_guidance is not None
        assert descriptor.limitations
        assert descriptor.llm_hint


@pytest.mark.parametrize("category", [StrategyCategoryTypes.trend, "trend"])
def test_list_strategies_by_category_returns_only_matching_strategies(category):
    strategies = list_strategies_by_category(category)

    assert strategies
    assert all(strategy.category == StrategyCategoryTypes.trend for strategy in strategies)


def test_list_strategies_by_category_rejects_unknown_category():
    with pytest.raises(ValueError):
        list_strategies_by_category("unknown")


def test_list_analysis_domains_returns_all_domains():
    index = list_analysis_domains()
    assert index.domains
    assert any(domain.id == AnalysisDomainTypes.technical_analysis for domain in index.domains.values())


@pytest.mark.parametrize("domain", [AnalysisDomainTypes.technical_analysis, "technical analysis"])
def test_list_strategies_by_domain_returns_only_matching_strategies(domain):
    strategies = list_strategies_by_domain(domain)

    assert strategies
    # Since all current strategies are technical analysis
    assert len(strategies) == len(list_strategies())


def test_list_strategies_by_domain_rejects_unknown_domain():
    with pytest.raises(ValueError):
        list_strategies_by_domain("unknown")


def test_get_catalog_strategy_id_map_matches_loaded_strategies():
    category_map = get_strategy_catalog_id_map()
    strategies = list_strategies()

    assert category_map
    assert set(category_map) == {strategy.category for strategy in strategies}

    for category, strategy_ids in category_map.items():
        expected_ids = [
            strategy.id for strategy in strategies if strategy.category == category
        ]
        assert set(strategy_ids) == set(expected_ids)
        assert strategy_ids == expected_ids


def test_get_strategy_by_id_returns_matching_descriptor():
    first_strategy = list_strategies()[0]

    descriptor = get_strategy_by_id(first_strategy.id)

    assert descriptor == first_strategy


def test_get_strategy_by_id_raises_for_unknown_strategy():
    with pytest.raises(ValueError, match="not found in catalog"):
        get_strategy_by_id("missing.strategy")
