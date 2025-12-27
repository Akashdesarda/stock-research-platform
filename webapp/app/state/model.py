from enum import Enum
from typing import Any

import polars as pl
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import AgentRunResult


class TickerChoice(Enum):
    desired = "Desired"
    index = "Index Based"
    all = "All"


class PreviewMethodChoice(Enum):
    head = "Head"
    tail = "Tail"
    desired = "Desired Range"
    random = "Random"


class AppState(BaseModel):
    # For Page: Playground --> data
    selected_exchange_data: str = Field(default_factory=str)
    ticker_choice_data: TickerChoice | None = None
    user_query_data: str | None = None
    preview_selection_data: bool = True
    query_manual_collection_data: pl.LazyFrame | list[pl.LazyFrame] | None = None
    preview_n_rows_data: int = 10
    preview_start_idx_data: int = 0
    preview_end_idx_data: int = 10
    preview_method_choice_data: PreviewMethodChoice | None = None
    query_prompt: str | None = None
    query_ai_collection_data: pl.LazyFrame | None = None
    agent_text_to_sql: AgentRunResult[Any] | None = None

    # TODO - remove later once determined if not needed
    user: str | None = None
    messages: list[dict] = Field(default_factory=list)
    selected_stock: str | None = None
    filters: dict[str, str] = Field(default_factory=dict)
    chat_mode: str = "analysis"
    debug: bool = False

    # global model config
    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # passthrough non-pydantic supported type like pl.LazyFrame
        validate_assignment=True,  # runtime safety during every assignment
    )
