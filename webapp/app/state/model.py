from enum import Enum

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai import AgentRunResult
from stocksense.ai.agents import CompanySummaryOutput, TextToSQLOutput


class PageKey(Enum):
    data = "data_explore"
    research = "research"


class TickerChoice(Enum):
    desired = "Desired"
    index = "Index Based"
    all = "All"


class PreviewMethodChoice(Enum):
    head = "Head"
    tail = "Tail"
    desired = "Desired Range"
    random = "Random"


class ResearchPageAvailableTools(Enum):
    company_summary = "Company Summary"
    dummy = "dummy"


class ResearchPhase(Enum):
    INIT = "init"
    SUMMARY_READY = "summary_ready"
    QA = "qa"


class DataPageAppState(BaseModel):
    # For Page: Playground --> data
    selected_exchange_data: str = Field(default_factory=str)
    preview_selection: bool = True
    # manual tab
    ticker_choice: TickerChoice | None = None
    query_user: str | None = None
    query_data_collection_manual: pl.LazyFrame | list[pl.LazyFrame] | None = None
    preview_n_rows_manual: int = 10
    preview_start_idx_manual: int = 0
    preview_end_idx_manual: int = 10
    preview_method_choice_manual: PreviewMethodChoice | None = None
    # ai tab
    query_prompt: str | None = Field(None, min_length=2)
    query_data_collection_ai: pl.LazyFrame | None = None
    agent_text_to_sql: AgentRunResult[TextToSQLOutput] | None = None
    preview_method_choice_ai: PreviewMethodChoice | None = None
    preview_n_rows_ai: int = 10
    preview_start_idx_ai: int = 0
    preview_end_idx_ai: int = 10

    # global model config
    @field_validator("query_user", mode="before")
    def _normalize_query_user(cls, v):
        # Treat empty or whitespace-only strings as None
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # passthrough non-pydantic supported type like pl.LazyFrame
        validate_assignment=True,  # runtime safety during every assignment
    )


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ResearchPageAppSate(BaseModel):
    selected_exchange: str | None = None
    selected_ticker: str | None = None

    # agent outputs
    company_summary: AgentRunResult[CompanySummaryOutput] | None = None

    # chat
    messages: list[ChatMessage] = []
    phase: ResearchPhase = ResearchPhase.INIT
