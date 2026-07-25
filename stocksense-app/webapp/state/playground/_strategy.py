import logging

import reflex as rx
from stocksense.config import get_settings
from stocksense.strategy.catalog import (
    AnalysisDomainIndex,
    AnalysisDomainTypes,
    StrategyCategoryTypes,
    StrategyDescriptor,
    get_strategy_by_id,
)
from stocksense.strategy.catalog.registry import (
    StrategyRegistry,
    filter_strategies,
    get_registry,
)

from webapp.state.shared import AgentRunMixin, TickerSelectionMixin
from webapp.types import RunState, TraceStep

logger = logging.getLogger("stocksense")
settings = get_settings()


def _resolve_analysis_domain(domain_key: str) -> AnalysisDomainTypes | None:
    if not domain_key:
        return None
    try:
        return AnalysisDomainTypes[domain_key]
    except KeyError:
        try:
            return AnalysisDomainTypes(domain_key)
        except ValueError:
            return None


class StrategyDiscoveryState(TickerSelectionMixin, AgentRunMixin, rx.State):
    # selection
    selected_domain: str = ""
    selected_strategy_category: str = ""
    selected_strategy: str = ""
    strategy: StrategyDescriptor | None = None

    # Run metadata
    run_state: str = RunState.idle.value
    trace_steps: list[TraceStep] = []

    # backend state
    _registry: StrategyRegistry = get_registry()

    @rx.var(cache=True)
    def analysis_domain(self) -> AnalysisDomainIndex:
        return self._registry.domains

    @rx.var(cache=True)
    def available_domain(self) -> list[str]:
        return list(self._registry.domains.domains.keys())

    @rx.var(cache=True)
    def available_strategy_category(self) -> dict[str, StrategyCategoryTypes]:
        domain = _resolve_analysis_domain(self.selected_domain)
        if domain is None:
            return {}
        return {
            i.name: i.strategies[next(iter(i.strategies))].category
            for i in self._registry.by_domain.get(domain, ())
        }

    @rx.var(cache=True)
    def available_strategy(self) -> dict[str, str]:
        if not self.selected_strategy_category:
            return {}
        domain = _resolve_analysis_domain(self.selected_domain)
        if domain is None:
            return {}
        category = self.available_strategy_category.get(self.selected_strategy_category)
        if category is None:
            return {}
        strategy = filter_strategies(domain=domain, category=category)

        return {i.name: i.id for i in strategy}

    @rx.var(cache=True)
    def strategy_json(self) -> str:
        return "" if self.strategy is None else self.strategy.model_dump_json(indent=2)

    @rx.event
    def set_domain(self, value: str) -> None:
        self.selected_domain = value
        self.selected_strategy_category = ""
        self.selected_strategy = ""
        self.strategy = None

    @rx.event
    def set_strategy_category(self, value: str) -> None:
        self.selected_strategy_category = value
        self.selected_strategy = ""
        self.strategy = None

    @rx.event
    def set_strategy(self, value: str) -> None:
        self.selected_strategy = value
        strategy_id = self.available_strategy.get(value)
        self.strategy = (
            get_strategy_by_id(strategy_id) if strategy_id is not None else None
        )
