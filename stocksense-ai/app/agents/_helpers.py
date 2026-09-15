import logging
import re
from functools import lru_cache

from agno.agent import Agent
from agno.exceptions import CheckTrigger, InputCheckError
from agno.run import RunContext
from app.prompt import PromptManager
from stocksense.config import get_settings
from stocksense.strategy.catalog import (
    AnalysisDomainCategoryDescriptor,
    AnalysisDomainDescriptor,
    AnalysisDomainTypes,
)
from stocksense.strategy.catalog.registry import get_registry

logger = logging.getLogger("stocksense")
settings = get_settings()
pm = PromptManager()

_WHITESPACE_RE = re.compile(r"\s+")


def get_history_table_columns() -> list[str]:
    # FIXME - Get actual columns from the table
    return [
        "date",
        "ticker",
        "company",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]


# SECTION - Strategy catalog index rendering


def _collapse(text: str) -> str:
    """Collapse YAML block-scalar newlines and whitespace runs to single spaces."""
    return _WHITESPACE_RE.sub(" ", text or "").strip()


def _join(values: list[str] | None, separator: str = "; ") -> str:
    """Collapse and join catalog phrases, dropping empty entries."""
    if not values:
        return ""
    return separator.join(filter(None, (_collapse(v) for v in values)))


def _sentence(text: str) -> str:
    """Collapse a summary and ensure it terminates with punctuation."""
    collapsed = _collapse(text)
    if collapsed and collapsed[-1] not in ".!?":
        collapsed += "."
    return collapsed


def _domain_label(descriptor: AnalysisDomainDescriptor) -> str | None:
    """Return the domain label, or None when the domain has no enum member."""
    raw = descriptor.id
    if isinstance(raw, AnalysisDomainTypes):
        return raw.value
    try:
        return AnalysisDomainTypes(str(raw).strip().lower()).value
    except ValueError:
        logger.warning(f"Skipping analysis domain without an enum member: {raw}")
        return None


def _strategy_count_label(count: int) -> str:
    if count <= 0:
        return "no strategies yet"
    return "1 strategy" if count == 1 else f"{count} strategies"


def _render_category(
    category_id: str,
    category: AnalysisDomainCategoryDescriptor,
    counts: dict[str, int],
    include_example_queries: bool,
) -> str:
    label = _strategy_count_label(counts.get(category_id, 0))
    parts = [f"- {category_id} ({label}): {_sentence(category.summary)}"]
    if use_if := _join(category.use_if):
        parts.append(f"Use if: {use_if}")
    if include_example_queries and (examples := _join(category.example_queries, " | ")):
        parts.append(f"Examples: {examples}")
    return " ".join(parts)


@lru_cache(maxsize=2)
def render_catalog_index(include_example_queries: bool = False) -> str:
    """Render a compact plain-text index of analysis domains and their categories.

    The size of this index scales with the number of CATEGORIES, not with the
    number of strategies, so it stays cheap to inject inline into a system prompt
    even as the catalog grows past 100 strategies. Per-category strategy counts
    are included so the model knows how broad a `list_strategies` call will be.
    """
    registry = get_registry()
    counts = {
        category.value: len(strategies)
        for category, strategies in registry.by_strategy_category.items()
    }

    blocks: list[str] = []
    for descriptor in registry.domains.domains.values():
        label = _domain_label(descriptor)
        if label is None:
            continue

        lines = [f"## {label}", _sentence(descriptor.summary)]
        if use_if := _join(descriptor.use_if):
            lines.append(f"Use if: {use_if}")
        if avoid_when := _join(descriptor.avoid_when):
            lines.append(f"Avoid when: {avoid_when}")
        if descriptor.categories:
            lines.append("Categories:")
            lines.extend(
                _render_category(category_id, category, counts, include_example_queries)
                for category_id, category in descriptor.categories.items()
            )
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


# SECTION - Agent instruction builders


@lru_cache(maxsize=1)
def _selection_instruction() -> str:
    return (
        pm.get_prompt(
            "strategy_selector",
            "selection_core",
            catalog_index=render_catalog_index(),
        )
        + "\n\n"
        + pm.get_prompt("strategy_selector", "conversational_output")
    )


@lru_cache(maxsize=1)
def _resolution_instruction() -> str:
    return (
        pm.get_prompt(
            "strategy_selector",
            "selection_core",
            catalog_index=render_catalog_index(),
        )
        + "\n\n"
        + pm.get_prompt("strategy_selector", "structured_output")
    )


def get_strategy_selection_instruction(
    run_context: RunContext | None = None, agent: Agent | None = None
) -> str:
    """Instructions for the conversational strategy selector agent."""
    return _selection_instruction()


def get_strategy_resolution_instruction(
    run_context: RunContext | None = None, agent: Agent | None = None
) -> str:
    """Instructions for the structured-output strategy resolver agent."""
    return _resolution_instruction()


def get_dataset_description_instruction(
    run_context: RunContext | None = None, agent: Agent | None = None
) -> str:
    """Returns SQL or metadata prompt based on context."""
    pm = PromptManager(strict_templates=False)
    deps = {}
    if run_context and hasattr(run_context, "dependencies"):
        deps = run_context.dependencies or {}
    elif agent and hasattr(agent, "dependencies"):
        deps = agent.dependencies or {}

    prompt_key = "sql_query_prompt" if deps.get("sql_query") else "metadata_prompt"
    return pm.get_prompt("dataset_description", prompt_key, **deps)


def dataset_description_input_validation(run_context: RunContext) -> None:
    # sourcery skip: invert-any-all
    """Pre-hook to validate dependency"""
    deps = {}
    if run_context and hasattr(run_context, "dependencies"):
        deps = run_context.dependencies or {}

    # deps should not be empty
    if len(deps) == 0:
        raise InputCheckError(
            "Dependencies are empty",
            check_trigger=CheckTrigger.VALIDATION_FAILED,
        )
    # deps must have exchange key
    if "exchange" not in deps:
        raise InputCheckError(
            "Dependencies must have 'exchange' key",
            check_trigger=CheckTrigger.VALIDATION_FAILED,
        )
    # deps must have either sql_query or ticker_identifier
    req_keys = ["sql_query", "ticker_identifier"]
    if not any(k in deps for k in req_keys):
        raise InputCheckError(
            "Dependencies must have either sql_query or ticker_identifier",
            check_trigger=CheckTrigger.VALIDATION_FAILED,
        )
