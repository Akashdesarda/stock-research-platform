import logging

from agno.agent import Agent
from app.agents._schema import SessionTitleOutput
from app.prompt import PromptManager
from app.skills.tools.sql import (
    verify_duckdb_sql_query_syntax,
    verify_sql_query_returns_data,
    verify_table_name,
)
from app.skills.tools.strategy import (
    EXCHANGE_KEY,
    TICKER_KEY,
    StockDBTools,
    StrategyDiscoveryTools,
)
from app.utils import async_sqlite_db, get_model
from stocksense.config import get_settings

from ._helpers import (
    dataset_description_input_validation,
    get_dataset_description_instruction,
    get_history_table_columns,
    get_strategy_resolution_instruction,
    get_strategy_selection_instruction,
)
from ._schema import (
    DatasetDescriptionOutput,
    DatasetSelection,
    StrategyParamSelection,
    StrategySelection,
    TextToSQLOutput,
)

logger = logging.getLogger("stocksense")
settings = get_settings()
pm = PromptManager()

session_title = Agent(
    id="session-title",
    name="Session title agent",
    description=pm.get_prompt("session_title", "description"),
    model=get_model(
        settings.ai.session_title_model,
        settings.get_model_api_keys(settings.ai.session_title_model),
        settings.get_model_base_url(settings.ai.session_title_model),
    ),
    instructions=pm.get_prompt("session_title", "instructions"),
    use_instruction_tags=True,
    output_schema=SessionTitleOutput,
    stream=False,
    debug_mode=True,
)

text_to_sql = Agent(
    name="Natural language to SQL agent",
    id="text-to-sql",
    description=pm.get_prompt("text_to_sql", "description"),
    model=get_model(
        settings.ai.text_to_sql_model,
        settings.get_model_api_keys(settings.ai.text_to_sql_model),
        settings.get_model_base_url(settings.ai.text_to_sql_model),
    ),
    instructions=pm.get_prompt(
        "text_to_sql", "instructions", columns=get_history_table_columns()
    ),
    use_instruction_tags=True,
    dependencies={"exchange": "nse"},  # default dependency
    add_dependencies_to_context=True,
    output_schema=TextToSQLOutput,
    tools=[
        verify_duckdb_sql_query_syntax,
        verify_table_name,
        verify_sql_query_returns_data,
    ],
    tool_call_limit=9,
    debug_mode=True,
)

company_summary = Agent(
    id="company-summary",
    name="Company summary chat agent",
    description=pm.get_prompt("company_summary", "description"),
    db=async_sqlite_db,
    model=get_model(
        model_name=settings.ai.company_summary_model,
        api_key=settings.get_model_api_keys(settings.ai.company_summary_model),
        base_url=settings.get_model_base_url(settings.ai.company_summary_model),
    ),
    instructions=pm.get_prompt("company_summary", "instructions"),
    expected_output=pm.get_prompt("company_summary", "expected_output"),
    stream=True,
    markdown=True,
    use_instruction_tags=True,
    tools=[StockDBTools()],
    session_state={
        EXCHANGE_KEY: None,  # Will be populated from dependencies
        TICKER_KEY: None,
    },
    add_session_state_to_context=True,
    enable_agentic_state=True,
    cache_session=True,
    add_history_to_context=True,
    read_chat_history=True,
    debug_mode=True,
)

dataset_description = Agent(
    id="dataset-description",
    name="Dataset description agent",
    description=pm.get_prompt("dataset_description", "description"),
    model=get_model(
        settings.ai.dataset_description_model,
        settings.get_model_api_keys(settings.ai.dataset_description_model),
        settings.get_model_base_url(settings.ai.dataset_description_model),
    ),
    instructions=get_dataset_description_instruction,
    use_instruction_tags=True,
    output_schema=DatasetDescriptionOutput,
    use_json_mode=True,
    pre_hooks=[dataset_description_input_validation],
    stream=False,
    debug_mode=True,
)

dataset_resolver = Agent(
    id="dataset-resolver",
    name="Dataset Resolver agent",
    description=pm.get_prompt("dataset_resolver", "description"),
    db=async_sqlite_db,
    model=get_model(
        settings.ai.dataset_resolver_model,
        settings.get_model_api_keys(settings.ai.dataset_resolver_model),
        settings.get_model_base_url(settings.ai.dataset_resolver_model),
    ),
    instructions=pm.get_prompt("dataset_resolver", "instructions"),
    use_instruction_tags=True,
    tools=[StockDBTools(include_tools=["list_registered_datasets"])],
    output_schema=DatasetSelection,
    stream=False,
    debug_mode=True,
)

strategy_selector = Agent(
    name="Strategy Chat agent",
    id="strategy-selector",
    description=pm.get_prompt("strategy_selector", "description"),
    db=async_sqlite_db,
    model=get_model(
        settings.ai.strategy_selector_model,
        settings.get_model_api_keys(settings.ai.strategy_selector_model),
        settings.get_model_base_url(settings.ai.strategy_selector_model),
    ),
    instructions=get_strategy_selection_instruction,
    use_instruction_tags=True,
    cache_session=True,
    add_history_to_context=True,
    # Cap history so older fully-formatted answers stop acting as few-shot
    # examples that make the agent repeat the report structure every turn.
    num_history_runs=3,
    tools=[
        StrategyDiscoveryTools(
            include_tools=["list_strategies", "get_strategy_details"]
        )
    ],
    tool_call_limit=4,
    markdown=True,
    stream=True,
    debug_mode=True,
)

strategy_resolver = Agent(
    name="Strategy resolver agent",
    id="strategy-resolver",
    description=pm.get_prompt("strategy_selector", "description"),
    db=async_sqlite_db,
    model=get_model(
        settings.ai.strategy_selector_model,
        settings.get_model_api_keys(settings.ai.strategy_selector_model),
        settings.get_model_base_url(settings.ai.strategy_selector_model),
    ),
    instructions=get_strategy_resolution_instruction,
    use_instruction_tags=True,
    tools=[
        StrategyDiscoveryTools(
            include_tools=["list_strategies", "get_strategy_details"]
        )
    ],
    tool_call_limit=4,
    output_schema=StrategySelection,
    stream=False,
    debug_mode=True,
)

strategy_param_resolver = Agent(
    name="Strategy param agent",
    id="strategy-param-resolver",
    db=async_sqlite_db,
    model=get_model(
        settings.ai.strategy_selector_model,
        settings.get_model_api_keys(settings.ai.strategy_selector_model),
        settings.get_model_base_url(settings.ai.strategy_selector_model),
    ),
    instructions=pm.get_prompt("strategy_selector", "parameter_resolution"),
    use_instruction_tags=True,
    tools=[StrategyDiscoveryTools(include_tools=["get_strategy_parameters"])],
    tool_call_limit=3,
    output_schema=StrategyParamSelection,
    stream=False,
    debug_mode=True,
)
