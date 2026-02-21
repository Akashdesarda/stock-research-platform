import re
from dataclasses import dataclass

import mlflow
from httpx import Client, AsyncClient
from mlflow.genai import load_prompt
from pydantic import BaseModel, Field
from pydantic_ai import Agent, AgentRunResult, RunContext

from stocksense.ai.models import get_model
from stocksense.config import get_settings

settings = get_settings()
# mlflow setup
mlflow.set_tracking_uri(f"{settings.common.base_url}:{settings.common.mlflow_port}")
mlflow.set_experiment("stocksense")
mlflow.pydantic_ai.autolog()


class CompanySummaryOutput(BaseModel):
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
            "✨ **AI Summary**\n\n"
            "---\n\n"
            f"{self.company_overview}\n\n"
            "---\n\n"
            f"{self.business_summary}\n\n"
            "---\n\n"
            f"{self.key_officers}\n\n"
            "---\n\n"
            f"{self.financial_highlights}\n\n"
            "---\n\n"
            f"{self.stock_performance}\n\n"
            "---\n\n"
            f"{self.summary_insight}\n\n"
        )

    @classmethod
    def from_text(cls, text: str) -> "CompanySummaryOutput":
        if not text or not text.strip():
            raise ValueError("Input text is empty.")

        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()

        # Remove optional heading
        cleaned = re.sub(
            r"^\s*✨?\s*\*{0,2}\s*AI\s*Summary\s*\*{0,2}\s*\n+",
            "",
            cleaned,
            count=1,
            flags=re.I,
        ).strip()

        # Split on separator lines (--- alone on a line)
        parts = [p.strip() for p in re.split(r"(?m)^\s*---\s*$", cleaned) if p.strip()]

        if len(parts) != 6:
            raise ValueError(f"Expected 6 sections separated by '---', found {len(parts)}.")

        return cls(
            company_overview=parts[0],
            business_summary=parts[1],
            key_officers=parts[2],
            financial_highlights=parts[3],
            stock_performance=parts[4],
            summary_insight=parts[5],
        )


@dataclass
class CompanyDataContextDependency:
    exchange: str
    ticker: str
    stockdb_api_base_url: str = (
        f"{settings.common.base_url}:{settings.stockdb.port}/api"
    )
    http_client: AsyncClient = AsyncClient(
        base_url=f'{settings.common.base_url}:{settings.stockdb.port}/api'
    )

async def company_summary(model_name: str, api_key: str) -> Agent[CompanyDataContextDependency, CompanySummaryOutput]:
    # initialize the agent
    agent: Agent[CompanyDataContextDependency, CompanySummaryOutput] = Agent(
        model=get_model(model_name, api_key),
        deps_type=CompanyDataContextDependency,
        output_type=CompanySummaryOutput,
        system_prompt=str(load_prompt("company_analysis_report_system").format()),
    )

    # REVIEW - See if vector embeddings can be used here instead of putting the text in prompt.
    @agent.instructions
    async def add_company_data(ctx: RunContext[CompanyDataContextDependency]) -> str:
        _ = await ctx.deps.http_client.get(
            f"/per-security/{ctx.deps.exchange}/{ctx.deps.ticker}/info"
        )
        ticker_info = _.json()

        return str(
            load_prompt("company_analysis_report_task").format(company_data=ticker_info)
        )

    return agent

def company_summary_qa(
    model_name: str, api_key: str, company_summary: CompanySummaryOutput
)-> Agent[None, str]:
    agent = Agent(
        model=get_model(model_name, api_key),
        system_prompt="You are a helpful finance analyst assistant.",
        output_type=str,
    )

    # TODO - Use vector embeddings instead of putting the whole summary in the system prompt.
    @agent.system_prompt
    def add_company_summary() -> str:
        return (
            "Use only the following company data while answering questions.\n"
            f"{company_summary.text_output()}"
        )

    return agent
