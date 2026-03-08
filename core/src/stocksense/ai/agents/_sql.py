from dataclasses import dataclass

from httpx import Client
from phoenix.client import AsyncClient as PhoenixAsyncClient
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from stocksense.ai import setup_phoenix_tracing
from stocksense.ai.utils import get_model
from stocksense.config import get_settings
from stocksense.data import StockDataDB
from stocksense.tools.sql import ParseError, SQLQueryValidator

settings = get_settings()

# Phoenix setup
setup_phoenix_tracing()
phoenix_client = PhoenixAsyncClient(
    base_url=f"{settings.common.base_url}:{settings.common.phoenix_port}"
)


@dataclass
class StockDBContextDependency:
    """Context that can be used as dependency injection by the Agent"""

    columns: list[str]
    table_name: str = StockDataDB.table_name
    stockdb_api_base_url: str = (
        f"{settings.common.base_url}:{settings.stockdb.port}/api"
    )
    http_client: Client = Client(
        base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api"
    )


class TextToSQLOutput(BaseModel):
    sql_query: str = Field(
        ..., description="Generated SQL query based on the user's request"
    )


async def text_to_sql(
    model_name: str, api_key: str
) -> Agent[StockDBContextDependency, TextToSQLOutput]:
    # initialize the agent
    agent: Agent[StockDBContextDependency, TextToSQLOutput] = Agent(
        model=get_model(model_name, api_key),
        name="text-to-sql",
        deps_type=StockDBContextDependency,
        output_type=TextToSQLOutput,
        instrument=True,
    )

    @agent.system_prompt
    async def add_system_prompt(
        ctx: RunContext[StockDBContextDependency],
    ) -> str:
        prompt = await phoenix_client.prompts.get(
            prompt_identifier="text-to-sql"
        )
        # NOTE - System prompt is static and does not need to be formatted with variables, but if needed, it can be done here.
        msg = prompt.format(
            variables={"table_name": "", "columns_to_used": ""}
        ).messages
        for m in msg:
            if m["role"] == "system":
                return m["content"]
        raise ValueError("No system prompt found in the retrieved prompt.")

    # Adding instruction to the agent
    @agent.instructions
    async def adding_tasks(ctx: RunContext[StockDBContextDependency]) -> str:
        prompt = await phoenix_client.prompts.get(
            prompt_identifier="text-to-sql"
        )
        # NOTE - System prompt is static and does not need to be formatted with variables, but if needed, it can be done here.
        msg = prompt.format(
            variables={
                "table_name": ctx.deps.table_name,
                "columns_to_used": ", ".join(ctx.deps.columns),
            }
        ).messages
        for m in msg:
            if m["role"] == "user":
                return m["content"]
        raise ValueError(
            "No user prompt/instruction found in the retrieved prompt."
        )

    @agent.tool
    def verify_duckdb_sql_query(
        ctx: RunContext[StockDBContextDependency], query: str
    ) -> str:
        """Use this tool to perform various validation checks. Bellow checks are available:
        1. Syntax wrt to DuckDB
        2. Table name

        Parameters
        ----------
        query : str
            SQL query to perform syntax validation on

        Returns
        -------
        str
            validated sql query

        Raises
        ------
        ModelRetry
            letting the LLM Model know whats the issue is
        """
        validator = SQLQueryValidator(query=query)
        try:
            return (
                validator.verify_syntax()
                # TODO - improved column verification logic
                # .verify_columns(ctx.deps.columns)
                .verify_table_name(ctx.deps.table_name)
                .run(optimize=False)
            )
        except (ValueError, ParseError) as e:
            raise ModelRetry(f"Invalid SQL query: {e}")

    return agent
