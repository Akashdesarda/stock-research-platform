import os
from dataclasses import dataclass

import mlflow
from httpx import Client
from mlflow.genai import load_prompt
from pydantic import BaseModel, Field
from pydantic_ai import Agent, AgentRunResult, RunContext

from stocksense.ai.models import get_model
from stocksense.config import get_settings

settings = get_settings(os.getenv("CONFIG_FILE"))
# mlflow setup
mlflow.set_tracking_uri(f"{settings.common.base_url}:{settings.common.mlflow_port}")
mlflow.set_experiment("stocksense")
mlflow.pydantic_ai.autolog()


class CompanySummary(BaseModel):
    company_overview: str = Field(..., description="High level overview of the company")
    business_summary: str = Field(
        ..., description="Summary regarding all the business the company does"
    )
    key_officers: str = Field(
        ..., description="Key people and office bearers of the company"
    )
    financial_highlights: str = Field(
        ...,
        description="All the financials highlights and key information of the company",
    )
    stock_performance: str = Field(
        ...,
        description="All the stock performance related highlights & key information of the company",
    )
    summary_insight: str = Field(
        ..., description="Executive insight & summary of the company"
    )

    def text_output(self) -> str:
        return (
            f"{self.company_overview}\n\n"
            f"{self.business_summary}\n\n"
            f"{self.key_officers}\n\n"
            f"{self.financial_highlights}\n\n"
            f"{self.stock_performance}\n\n"
            f"{self.summary_insight}\n\n"
        )


@dataclass
class CompanyDataContextDependency:
    exchange: str
    ticker: str
    stockdb_api_base_url: str = (
        f"{settings.common.base_url}:{settings.stockdb.port}/api"
    )
    http_client: Client = Client(
        base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api"
    )


def company_summary(
    model_name: str, api_key: str, exchange: str, ticker: str
) -> AgentRunResult[CompanySummary]:
    # initialize the agent
    agent = Agent(
        model=get_model(model_name, api_key),
        deps_type=CompanyDataContextDependency,
        output_type=CompanySummary,
        system_prompt=str(load_prompt("company_analysis_report_system").format()),
    )

    @agent.instructions
    def add_company_data(ctx: RunContext[CompanyDataContextDependency]) -> str:
        ticker_info = ctx.deps.http_client.get(
            f"/per-security/{ctx.deps.exchange}/{ctx.deps.ticker}"
        ).json()

        return str(
            load_prompt("company_analysis_report_task").format(company_data=ticker_info)
        )

    # Running the agent to generate the report
    ctx_deps = CompanyDataContextDependency(exchange, ticker)

    return agent.run_sync(
        "Give me detail information given company data", deps=ctx_deps
    )


def company_summary_qa(model_name: str, api_key: str, company_summary: CompanySummary):
    agent = Agent(
        model=get_model(model_name, api_key),
        system_prompt="You are a finance analyst helping assistant.",
        output_type=str,
    )

    @agent.system_prompt
    def add_company_summary() -> str:
        return (
            "Use only the following company data while answering questions.\n"
            f"{company_summary.text_output()}"
        )

    return agent
