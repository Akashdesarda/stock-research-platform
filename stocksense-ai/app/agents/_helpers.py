import logging

from agno.agent import Agent
from agno.exceptions import CheckTrigger, InputCheckError
from agno.run import RunContext
from app.prompt import PromptManager
from app.skills.tools.strategy import (
    SELECTED_CATEGORY_KEY,
    SELECTED_DOMAIN_KEY,
    SELECTED_STRATEGY_KEY,
)
from stocksense.config import get_settings

logger = logging.getLogger("stocksense")
settings = get_settings()
pm = PromptManager()


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


def get_strategy_selection_instruction(
    run_context: RunContext | None = None, agent: Agent | None = None
) -> str:
    session_state = {}
    if (
        run_context is not None
        and getattr(run_context, "session_state", None) is not None
    ):
        session_state = run_context.session_state
    elif agent is not None and getattr(agent, "session_state", None) is not None:
        session_state = agent.session_state

    return pm.get_prompt(
        "strategy_selector",
        "instructions",
        selected_domain=session_state.get(SELECTED_DOMAIN_KEY, None),
        selected_category=session_state.get(SELECTED_CATEGORY_KEY, None),
        selected_strategy=session_state.get(SELECTED_STRATEGY_KEY, None),
    )


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
