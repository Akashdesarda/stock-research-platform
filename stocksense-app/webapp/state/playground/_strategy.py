import contextlib
import json
import logging
import uuid
from typing import Any

import polars as pl
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

_NUMERIC_PARAM_TYPES = ("int", "float")


# Try multiple ways to parse domain keys since they can come from different sources
# (enum names, enum values, or raw strings from the UI)
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


def _parameter_specs(parameters: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten a strategy's ``parameters`` blob into render-ready string rows.

    The catalog types ``parameters`` as ``dict[str, Any]``, so every field is
    optional and the value may not even be a mapping. Everything is coerced to
    ``str`` here to keep the rows friendly to Reflex vars and tables.
    """
    specs: list[dict[str, str]] = []
    for name, meta in parameters.items():
        # Handle both full parameter definitions and shorthand notation where
        # the value itself is the default (e.g., "period: 14" instead of "period: {default: 14}")
        if not isinstance(meta, dict):
            meta = {"default": meta}

        param_type = str(meta.get("type", "") or "")
        min_v, max_v = meta.get("min"), meta.get("max")
        default = meta.get("default")
        specs.append({
            "name": name,
            "type": param_type,
            "default": "" if default is None else str(default),
            "min": "" if min_v is None else str(min_v),
            "max": "" if max_v is None else str(max_v),
            "range": (
                f"{min_v}–{max_v}" if min_v is not None and max_v is not None else ""
            ),
            "description": str(meta.get("description", "") or ""),
        })
    return specs


# Convert user input strings to their proper types with friendly error messages
# Returns a tuple of (converted_value, error_message) for flexible error handling
def _cast_param(value: str, param_type: str) -> tuple[Any, str]:
    """Cast a raw input string to ``param_type``, returning ``(value, error)``."""
    if param_type == "int":
        try:
            return int(value), ""
        except ValueError:
            return None, "Must be a whole number"
    if param_type == "float":
        try:
            return float(value), ""
        except ValueError:
            return None, "Must be a number"
    if param_type == "bool":
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes"):
            return True, ""
        if normalized in ("false", "0", "no"):
            return False, ""
        return None, "Must be true or false"
    return value, ""


def _validate_param(value: str, spec: dict[str, str]) -> str:
    """Return a human readable error for ``value``, or an empty string if valid."""
    param_type = spec["type"]
    # Empty inputs are always valid - they tell the backend to use strategy defaults
    # This lets users override only what they need without filling every field
    if not value.strip():
        return ""

    casted, error = _cast_param(value, param_type)
    if error:
        return error
    if param_type not in _NUMERIC_PARAM_TYPES:
        return ""

    if spec["min"]:
        minimum, _ = _cast_param(spec["min"], param_type)
        if minimum is not None and casted < minimum:
            return f"Must be ≥ {spec['min']}"
    if spec["max"]:
        maximum, _ = _cast_param(spec["max"], param_type)
        if maximum is not None and casted > maximum:
            return f"Must be ≤ {spec['max']}"
    return ""


class StrategyDiscoveryState(TickerSelectionMixin, AgentRunMixin, rx.State):
    # Manages the hierarchical selection flow: Domain → Category → Strategy

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
        # Build a map of category names to their types by peeking at the first strategy
        # in each category (all strategies in a category share the same type)
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
        # Convert domain IDs to human-readable labels, handling both enum values
        # and plain strings for flexible display in the UI
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
        return _parameter_specs(self.strategy.parameters)

    @rx.event
    def set_domain(self, value: str) -> None:
        self.selected_domain = value
        # Cascade reset: changing domain invalidates category and strategy selections
        # to prevent showing incompatible options
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

    # Conversational AI interface for strategy discovery - maintains session state
    # across multiple turns so the agent remembers context from previous questions
    run_state: str = RunState.idle.value
    # Agno session for the conversation; minted on the first user message.
    # (Also declared on ChatMixin — kept here for clarity of this page's contract.)
    current_session_id: str = ""

    @rx.event
    def submit_example(self, text: str):
        """Fill the prompt from an empty-state chip and submit (click = send)."""
        # Quick-start from example prompts: populate input and auto-submit
        # Prevents double-submission if a generation is already running
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
            # Session lifecycle: create once on first message, reuse for follow-ups
            # This enables multi-turn conversations where the AI remembers prior context
            first_turn = not self.current_session_id
            if first_turn:
                self.current_session_id = str(uuid.uuid4())
            # Do not set run_state=generating here — stream_agent_run(manage_lifecycle=True)
            # owns the busy window and will no-op if we mark generating first.
            self.messages.append(Message(role="user", content=prompt))
            self.prompt = ""  # rest the user prompt input field.
            self.messages.append(Message(role="assistant", content=""))
            session_id = self.current_session_id

        # Stream the AI response in real-time while managing the busy state automatically
        # The lifecycle manager prevents race conditions during concurrent requests
        await self.stream_agent_run(
            agent_id="strategy-selector",
            message=prompt,
            session_id=session_id,
            on_content=self._on_content,
            on_complete=self._on_answer_completed,
            manage_lifecycle=True,
        )
        if first_turn:
            # Give the session a meaningful name based on the first question
            # Fire-and-forget pattern: don't block the response on this cosmetic update
            return StrategyAIState.rename_session(session_id, prompt)

    @rx.event(background=True)
    async def rename_session(self, session_id: str, prompt: str):
        """Best-effort session rename; fire-and-forget from generate_answer."""
        # Best-effort rename - if it fails, no big deal, the session still works
        # Suppressing exceptions keeps the main flow clean and responsive
        with contextlib.suppress(Exception):
            await self.ai_client._apatch(
                endpoint="/debug/session/rename",
                data={
                    "session_id": session_id,
                    "session_type": "agent",
                    "content": [prompt],
                },
            )
            logger.debug(f"renamed strategy-selector session: {session_id}")

    async def _on_content(self, event: RunContentEvent):
        """Append each text delta to the streaming assistant message."""
        async with self:
            self._update_last_assistant(append_content=event.content or "")

    async def _on_answer_completed(self, completed: RunCompletedEvent):
        async with self:
            self._update_last_assistant(content=completed.content or "")
            self.agent_status_message = ""


class ApplyStrategyState(TickerSelectionMixin, AgentRunMixin, rx.State):
    """State for apply strategy"""

    # Selection state
    select_dataset_dropdown: str = ""
    select_strategy_dropdown: str = ""
    select_dataset_id: str = ""
    select_strategy_id: str = ""

    # Parameter state is split into three layers for clean separation of concerns:
    available_params: dict[str, Any] = {} # raw API response
    param_specs: list[dict[str, str]] = [] # flattened, UI-ready rows with metadata
    param_inputs: dict[str, str] = {} # user inputs
    param_errors: dict[str, str] = {}
    params_error: str = ""

    # LLM Agent state
    run_state: str = RunState.idle.value
    # Agno session for the conversation; minted on the first user message.
    # (Also declared on ChatMixin — kept here for clarity of this page's contract.)
    current_session_id: str = ""

    @rx.var(cache=True)
    async def available_datasets(self) -> pl.DataFrame:
        async with self._stockdb_client() as client:
            response = await client.get("/operation/data")
            datasets = pl.DataFrame([
                {"id": i["dataset_id"], "name": i["name"]} for i in response.json()
            ])
            # Format dropdown labels as "Name (ID)" for easy identification
            # while keeping the actual ID separate for API calls
            datasets = datasets.with_columns(
                dropdown=pl.col("name") + " (" + pl.col("id") + ")"
            )
            return datasets

    @rx.var(cache=True)
    async def available_datasets_dropdown(self) -> list[str]:
        _ = await self.available_datasets
        return _.select("dropdown").to_series().to_list()

    @rx.var(cache=True)
    async def available_strategies(self) -> pl.DataFrame:
        async with self._stockdb_client() as client:
            response = await client.get("/strategy")
            strategies = pl.DataFrame([
                {"id": i["id"], "name": i["name"]} for i in response.json()
            ])
            strategies = strategies.with_columns(
                dropdown=pl.col("name") + " (" + pl.col("id") + ")"
            )
            return strategies

    @rx.var(cache=True)
    async def available_strategies_dropdown(self) -> list[str]:
        _ = await self.available_strategies
        return _.select("dropdown").to_series().to_list()

    @rx.var(cache=True)
    def param_rows(self) -> list[dict[str, str]]:
        """Specs merged with the current input value and error, for `rx.foreach`."""
        # Merge parameter specs with current input state for rendering
        # Each row gets its value, error, and UI hints for a complete form field
        rows: list[dict[str, str]] = []
        for spec in self.param_specs:
            name, param_type, default = spec["name"], spec["type"], spec["default"]
            rows.append({
                **spec,
                "value": self.param_inputs.get(name, ""),
                "error": self.param_errors.get(name, ""),
                "placeholder": default or "value",
                # Smart input types: numeric fields get number inputs with steppers,
                # everything else stays text for maximum flexibility (like column names)
                "input_type": (
                    "number" if param_type in _NUMERIC_PARAM_TYPES else "text"
                ),
                "step": "1" if param_type == "int" else "any",
                "hint": (
                    f"Default: {default}"
                    if default
                    else "Blank uses the strategy default"
                ),
            })
        return rows

    @rx.var(cache=True)
    def has_params(self) -> bool:
        return len(self.param_specs) > 0

    @rx.var(cache=True)
    def has_param_errors(self) -> bool:
        return any(self.param_errors.values())

    @rx.var(cache=True)
    def resolved_params(self) -> dict[str, Any]:
        """Cast, validated payload for `POST /strategy/apply`"""
        # Build the final API payload by casting and validating each parameter
        # Blank or invalid inputs are skipped so the backend uses its defaults
        payload: dict[str, Any] = {}
        for spec in self.param_specs:
            raw = self.param_inputs.get(spec["name"], "")
            if not raw.strip() or _validate_param(raw, spec):
                continue
            value, error = _cast_param(raw, spec["type"])
            if error:
                continue
            payload[spec["name"]] = value
        return payload

    @rx.var(cache=True)
    def resolved_params_json(self) -> str:
        return json.dumps(self.resolved_params, indent=2, default=str)

    @rx.var(cache=True)
    def can_apply(self) -> bool:
        # All green lights: dataset selected, strategy selected, and no validation errors
        # This gates the "Apply" button to prevent incomplete submissions
        return bool(
            self.select_dataset_id
            and self.select_strategy_id
            and not self.params_error
            and not self.has_param_errors
        )

    @rx.event
    async def set_select_dataset_id(self, value: str):
        self.select_dataset_dropdown = value
        _ = await self.available_datasets
        self.select_dataset_id = (
            _.filter(pl.col("dropdown") == value).select("id").item()
        )

    @rx.event
    async def set_select_strategy_id(self, value: str):
        self.select_strategy_dropdown = value
        _ = await self.available_strategies
        self.select_strategy_id = (
            _.filter(pl.col("dropdown") == value).select("id").item()
        )
        # Auto-load parameters whenever the strategy changes
        # This keeps the form in sync with the selected strategy's requirements
        await self.load_params()

    @rx.event
    async def load_params(self):
        """Fetch the selected strategy's parameters and seed the input fields."""
        # Fetch parameter definitions from the API and initialize the input form
        # Clears any stale state first to avoid mixing parameters from different strategies
        self._clear_params()
        if not self.select_strategy_id:
            return
        try:
            async with self._stockdb_client() as client:
                response = await client.get(f"/strategy/id/{self.select_strategy_id}")
                response.raise_for_status()
                self.available_params = response.json().get("parameters", {}) or {}
        except Exception as e:
            logger.exception("failed to load strategy parameters", exc_info=e)
            self.params_error = f"Failed to load parameters: {e}"
            return
        self.param_specs = _parameter_specs(self.available_params)
        self.reset_params()

    @rx.event
    def set_param_value(self, name: str, value: str):
        """Update a single parameter and re-validate just that field."""
        spec = next((s for s in self.param_specs if s["name"] == name), None)
        if spec is None:
            return
        # Live validation: check the input immediately as the user types
        # Keeps error messages in sync without waiting for form submission
        self.param_inputs = {**self.param_inputs, name: value}
        self.param_errors = {
            **self.param_errors,
            name: _validate_param(value, spec),
        }

    @rx.event
    def reset_params(self):
        """Reset every parameter back to its catalog default."""
        # Restore all parameters to their catalog defaults
        # Useful when users want to start fresh after experimenting with values
        self.param_inputs = {s["name"]: s["default"] for s in self.param_specs}
        self.param_errors = dict.fromkeys(self.param_inputs, "")

    @rx.event
    def clear_params(self):
        """Blank every parameter so the backend defaults are used."""
        # Blank out all inputs to let the backend apply its own defaults
        # Different from reset: this removes user overrides entirely
        self.param_inputs = dict.fromkeys(self.param_inputs, "")
        self.param_errors = dict.fromkeys(self.param_inputs, "")

    def _clear_params(self):
        self.available_params = {}
        self.param_specs = []
        self.param_inputs = {}
        self.param_errors = {}
        self.params_error = ""
