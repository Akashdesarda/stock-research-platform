from dataclasses import dataclass

import mlflow
from httpx import Client
from mlflow.genai import load_prompt
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from stocksense.ai.models import get_model
from stocksense.config import Settings
from stocksense.data import StockDataDB
from stocksense.tools.sql import ParseError, SQLQueryValidator

settings = Settings()
# mlflow setup
mlflow.set_tracking_uri(f"{settings.common.base_url}:{settings.common.mlflow_port}")
mlflow.set_experiment("stocksense")
mlflow.pydantic_ai.autolog()


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


def text_to_sql(
    model_name: str, api_key: str
) -> Agent[StockDBContextDependency, TextToSQLOutput]:
    # initialize the agent
    agent = Agent(
        model=get_model(model_name, api_key),
        deps_type=StockDBContextDependency,
        output_type=TextToSQLOutput,
        system_prompt=str(load_prompt("text_to_sql_system").format()),
    )

    # Adding instruction to the agent
    @agent.instructions
    def adding_tasks(ctx: RunContext[StockDBContextDependency]) -> str:
        # getting current available columns from stockdb
        # columns = (
        #     ctx.deps.http_client.get(
        #         "/per-security/nse/tcs/history",
        #         params={"interval": "1d", "period": "1d"},
        #     )
        #     .json()[0]
        #     .keys()
        # )
        return str(
            load_prompt("text_to_sql_task").format(
                table_name=ctx.deps.table_name,
                columns_to_used=", ".join(ctx.deps.columns),
            )
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
