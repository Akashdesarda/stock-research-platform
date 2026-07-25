import logging

import reflex as rx
from stocksense.config import get_settings
from stocksense.strategy.catalog import StrategyCatalogIndex

from webapp.state.shared import AgentRunMixin, TickerSelectionMixin
from webapp.types import RunState, TraceStep

logger = logging.getLogger("stocksense")
settings = get_settings()


class DiscoveryState(TickerSelectionMixin, AgentRunMixin):
    run_state: str = RunState.idle.value
    trace_steps: list[TraceStep] = []

    @rx.var
    async def strategy_index(self) -> list[StrategyCatalogIndex]:
        async with self._stockdb_client() as client:
            _ = await client.get("/strategy/catalog")
            return [StrategyCatalogIndex.model_validate(item) for item in _.json()]
