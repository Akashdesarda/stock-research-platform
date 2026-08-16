import logging
import uuid

import reflex as rx
from agno.run.agent import RunCompletedEvent, RunContentEvent
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

from webapp.state.shared import AgentRunMixin, ChatMixin, TickerSelectionMixin
from webapp.types import Message, RunState, TraceStep

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

    @rx.var(cache=True)
    def strategy_category_label(self) -> str:
        if self.strategy is None:
            return ""
        category = self.strategy.category
        return category.value if hasattr(category, "value") else str(category)

    @rx.var(cache=True)
    def domain_id_labels(self) -> dict[str, str]:
        labels: dict[str, str] = {}
        for key, domain in self._registry.domains.domains.items():
            domain_id = domain.id
            labels[key] = (
                domain_id.value.title()
                if hasattr(domain_id, "value")
                else str(domain_id)
            )
        return labels

    @rx.var(cache=True)
    def strategy_market_regimes(self) -> list[str]:
        if self.strategy is None:
            return []
        return [
            r.value if hasattr(r, "value") else str(r)
            for r in self.strategy.market_regimes
        ]

    @rx.var(cache=True)
    def strategy_time_horizons(self) -> list[str]:
        if self.strategy is None:
            return []
        return [
            h.value if hasattr(h, "value") else str(h)
            for h in self.strategy.time_horizons
        ]

    @rx.var(cache=True)
    def strategy_parameter_rows(self) -> list[dict[str, str]]:
        if self.strategy is None:
            return []
        rows: list[dict[str, str]] = []
        for name, meta in self.strategy.parameters.items():
            if not isinstance(meta, dict):
                rows.append({
                    "name": name,
                    "type": "",
                    "default": str(meta),
                    "range": "",
                    "description": "",
                })
                continue
            min_v, max_v = meta.get("min"), meta.get("max")
            range_str = (
                f"{min_v}–{max_v}" if min_v is not None and max_v is not None else ""
            )
            rows.append({
                "name": name,
                "type": str(meta.get("type", "")),
                "default": (
                    "" if meta.get("default") is None else str(meta["default"])
                ),
                "range": range_str,
                "description": str(meta.get("description", "")),
            })
        return rows

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


# NOTE - ChatMixin must be first so _record_step attaches agent trace steps to the assistant message (inline_steps)
class StrategyAIState(ChatMixin, TickerSelectionMixin, AgentRunMixin, rx.State):
    """State for multi-turn strategy-selector chat (no pre-chat bootstrap step)"""

    run_state: str = RunState.idle.value
    # Agno session for the conversation; minted on the first user message.
    # (Also declared on ChatMixin — kept here for clarity of this page's contract.)
    current_session_id: str = ""

    @rx.event
    def submit_example(self, text: str):
        """Fill the prompt from an empty-state chip and submit (click = send)."""
        if self.run_state == RunState.generating.value:
            return
        self.prompt = text
        yield StrategyAIState.generate_answer

    @rx.event(background=True)
    async def generate_answer(self):
        if self.run_state == RunState.generating.value:
            return

        prompt = self.prompt.strip()
        if not prompt:
            return

        async with self:
            # First turn: create a session. Later turns reuse it for multi-turn QA.
            first_turn = not self.current_session_id
            if first_turn:
                self.current_session_id = str(uuid.uuid4())
            # Do not set run_state=generating here — stream_agent_run(manage_lifecycle=True)
            # owns the busy window and will no-op if we mark generating first.
            self.messages.append(Message(role="user", content=prompt))
            self.prompt = ""  # rest the user prompt input field.
            self.messages.append(Message(role="assistant", content=""))
            session_id = self.current_session_id

        await self.stream_agent_run(
            agent_id="strategy-selector",
            message=prompt,
            session_id=session_id,
            on_content=self._on_content,
            on_complete=self._on_answer_completed,
            manage_lifecycle=True,
        )
        # Title the session once at conversation start (first user message only).
        if first_turn:
            async with self:
                await self.ai_client._apatch(
                    endpoint="/debug/session/rename",
                    data={
                        "session_id": session_id,
                        "session_type": "agent",
                        "content": [prompt],
                    },
                )
                logger.debug(f"renamed strategy-selector session {session_id}")

    async def _on_content(self, event: RunContentEvent):
        """Append each text delta to the streaming assistant message."""
        async with self:
            self._update_last_assistant(append_content=event.content or "")

    async def _on_answer_completed(self, completed: RunCompletedEvent):
        async with self:
            self._update_last_assistant(content=completed.content or "")
            self.agent_status_message = ""
