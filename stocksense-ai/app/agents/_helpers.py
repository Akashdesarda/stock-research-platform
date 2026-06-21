import logging

from agno.agent import Agent
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
