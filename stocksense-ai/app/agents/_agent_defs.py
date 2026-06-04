import logging

from agno.agent import Agent
from agno.run import RunContext
from stocksense.config import get_settings

from app.utils import get_model
from app.prompt import PromptManager
from app.skills.tools.sql import (
    verify_duckdb_sql_query_syntax,
    verify_table_name,
    verify_sql_query_returns_data,
)
from app.skills.tools.strategy import (
    StrategyDiscoveryTools,
    SELECTED_DOMAIN_KEY,
    SELECTED_CATEGORY_KEY,
    SELECTED_STRATEGY_KEY,
)
from ._output_schema import TextToSQLOutput


logger = logging.getLogger("stocksense")
settings = get_settings()
pm = PromptManager()


def _get_history_table_columns() -> list[str]:
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


def _get_strategy_selection_instruction(
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


text_to_sql = Agent(
    name="text-to-sql",
    description=pm.get_prompt("text_to_sql", "description"),
    model=get_model(
        settings.ai.text_to_sql_model,
        settings.get_model_api_keys(settings.ai.text_to_sql_model),
        settings.get_model_base_url(settings.ai.text_to_sql_model),
    ),
    instructions=pm.get_prompt(
        "text_to_sql", "instructions", columns=_get_history_table_columns()
    ),
    use_instruction_tags=True,
    dependencies={"exchange": "nse"},  # default dependency
    output_schema=TextToSQLOutput,
    use_json_mode=True,
    tools=[
        verify_duckdb_sql_query_syntax,
        verify_table_name,
        verify_sql_query_returns_data,
    ],
    debug_mode=True,
)

strategy_selector = Agent(
    name="strategy-selector",
    description=pm.get_prompt("strategy_selector", "description"),
    model=get_model(
        settings.ai.strategy_selector_model,
        settings.get_model_api_keys(settings.ai.strategy_selector_model),
        settings.get_model_base_url(settings.ai.strategy_selector_model),
    ),
    instructions=_get_strategy_selection_instruction,
    expected_output=pm.get_prompt("strategy_selector", "expected_output"),
    additional_context=pm.get_prompt("strategy_selector", "additional_context"),
    session_state={
        SELECTED_DOMAIN_KEY: None,
        SELECTED_CATEGORY_KEY: None,
        SELECTED_STRATEGY_KEY: None,
    },
    use_instruction_tags=True,
    add_session_state_to_context=True,
    tools=[StrategyDiscoveryTools()],
    markdown=True,
    stream=True,
)
