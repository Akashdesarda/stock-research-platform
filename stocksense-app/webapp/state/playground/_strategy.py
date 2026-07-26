import logging

import reflex as rx
from stocksense.config import get_settings
from stocksense.strategy.catalog import (
    AnalysisDomainIndex,
    list_analysis_domains,
)

from webapp.state.shared import AgentRunMixin, TickerSelectionMixin
from webapp.types import RunState, TraceStep

logger = logging.getLogger("stocksense")
settings = get_settings()


class StrategyDiscoveryState(TickerSelectionMixin, AgentRunMixin, rx.State):
    # selection
    selected_domain: str = ""

    # Run metadata
    run_state: str = RunState.idle.value
    trace_steps: list[TraceStep] = []

    @rx.var(cache=True)
    def analysis_domain(self) -> AnalysisDomainIndex:
        return list_analysis_domains()

    @rx.var(cache=True)
    def available_domain(self) -> list[str]:
        return list(self.analysis_domain.domains.keys())

    # @rx.var(cache=True)
    # async def catalog_strategy_id_map(self) -> dict:
    #     # async with self._stockdb_client() as client:
    #     #     response = await client.get("/strategy/id")
    #     #     response.raise_for_status()
    #     # return response.json()
    #     return get_strategy_catalog_id_map()

    # @rx.var
    # async def available_category(self) -> list[str]:
    #     strategy_idx = await self.strategy_index
    #     return sorted({i.domain.value for i in strategy_idx})
