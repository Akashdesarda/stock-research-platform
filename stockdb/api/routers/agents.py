import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterable
from zoneinfo import ZoneInfo

import polars as pl
from fastapi import APIRouter, HTTPException, status
from httpx import AsyncClient
from pydantic_ai import ThinkingPart, ToolCallPart
from stocksense.ai.agents import (
    CompanyDataContextDependency,
    StockDBContextDependency,
    company_summary,
    company_summary_qa,
    text_to_sql,
)
from stocksense.ai.utils import (
    history_messages_to_json,
    json_to_history_messages,
)
from stocksense.config import get_settings
from stocksense.data import StockDataDB

from api.models import (
    APITags,
    CompanySummaryAgent,
    CompanySummaryAgentQA,
    PromptCacheInput,
    ResultChunk,
    TextToSQLAgent,
    ThinkingChunk,
    ToolCallChunk,
)

logger = logging.getLogger("stockdb")
settings = get_settings()
http_client: AsyncClient = AsyncClient(
    base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api",
    timeout=None,
    follow_redirects=True,
)

StreamEvent = ThinkingChunk | ToolCallChunk | ResultChunk


@dataclass
class StreamState:
    sent_tool_calls: set[str] = field(default_factory=set)
    thinking_parts: list[str] = field(default_factory=list)
    last_thinking_content: str | None = None


def _company_summary_prompt(exchange: str, ticker: str) -> str:
    return f"Generate a company summary for {ticker} on {exchange} exchange."


def _extract_thinking_delta(
    content: str, previous_content: str | None
) -> tuple[str | None, str]:
    if previous_content is None:
        return content, content
    if content == previous_content:
        return None, previous_content
    if content.startswith(previous_content):
        return content[len(previous_content) :], content
    return content, content


def _handle_response_part(
    part: object, stream_state: StreamState
) -> ThinkingChunk | ToolCallChunk | None:
    """Helper function to convert different response parts into unified stream events"""
    # 1. Handle Thinking/Reasoning
    if isinstance(part, ThinkingPart):
        if not part.has_content():
            return None

        thinking_delta, stream_state.last_thinking_content = (
            _extract_thinking_delta(
                part.content, stream_state.last_thinking_content
            )
        )
        if not thinking_delta:
            return None

        stream_state.thinking_parts.append(thinking_delta)
        return ThinkingChunk(content=thinking_delta)

    # 2. Handle Tool Calls (Visibility)
    if isinstance(part, ToolCallPart):
        # Only yield if this is a new tool call to avoid spamming the stream
        if part.tool_call_id in stream_state.sent_tool_calls:
            return None
        stream_state.sent_tool_calls.add(part.tool_call_id)
        return ToolCallChunk(
            tool_name=part.tool_name,
            args=part.args_as_dict() if part.args else None,
        )

    return None


async def _stream_structured_agent_run(
    result: Any,
    stream_state: StreamState,
) -> AsyncIterable[StreamEvent]:
    async for response, _ in result.stream_responses():
        for part in response.parts:
            stream_event = _handle_response_part(part, stream_state)
            if stream_event is not None:
                yield stream_event

    async for partial_model in result.stream_output(debounce_by=0.1):
        yield ResultChunk(content=partial_model)


# SECTION - FastAPI Router and Endpoints
router = APIRouter(prefix="/api/agents", tags=[APITags.agent])


@router.post("/text-to-sql")
async def text_to_sql_agent(
    input: TextToSQLAgent,
) -> AsyncIterable[StreamEvent]:
    """Agent that converts natural language text to SQL query"""
    history_data = StockDataDB(
        settings.stockdb.data_base_path
        / f"{input.exchange.value}/ticker_history"
    )
    cols = history_data.table_data.collect_schema().names()
    context = StockDBContextDependency(columns=cols)

    stream_state = StreamState()

    agent = await text_to_sql(
        model_name=input.model, api_key=settings.get_model_api_keys(input.model)
    )

    try:
        async with agent.run_stream(input.prompt, deps=context) as result:
            async for stream_event in _stream_structured_agent_run(
                result, stream_state
            ):
                yield stream_event
    except Exception as e:
        # Handle any exceptions that occur during the agent execution
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while running the agent: {str(e)}",
        ) from e


@router.post("/company-summary")
async def company_summary_agent(
    input: CompanySummaryAgent,
) -> AsyncIterable[StreamEvent]:
    """Agent that generates a summary for a given company"""
    context = CompanyDataContextDependency(
        exchange=input.exchange.value,
        ticker=input.ticker,
    )
    stream_state = StreamState()

    agent = await company_summary(
        model_name=input.model, api_key=settings.get_model_api_keys(input.model)
    )
    try:
        async with agent.run_stream(
            "Give me detail information with respect to the given company data",
            deps=context,
        ) as result:
            async for stream_event in _stream_structured_agent_run(
                result, stream_state
            ):
                yield stream_event

            final_output = await result.get_output()

        # Persist company summary as cache
        final_thinking = "".join(stream_state.thinking_parts).strip() or None
        payload = PromptCacheInput(
            prompt=_company_summary_prompt(input.exchange.value, input.ticker),
            agent="company-summary",
            model=input.model,
            response=final_output.text_output(),
            thinking=final_thinking,
            ttl=1,  # Cache for 1 day
        )
        cache_response = await http_client.put(
            "/operation/prompt/cache", json=payload.model_dump()
        )
        cache_response.raise_for_status()
        logger.debug(
            f"Cached company summary for {input.ticker} on {input.exchange.value}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while running the agent: {str(e)}",
        ) from e


@router.post("/company-summary-qa")
async def company_summary_qa_agent(
    input: CompanySummaryAgentQA,
) -> AsyncIterable[str]:
    """Agent that answers questions about a given company based on its summary"""
    chat_history = StockDataDB(
        settings.stockdb.data_base_path / "common/chat_history"
    )
    message_df = chat_history.polars_filter(
        pl.col("session_id") == input.session_id
    ).collect()
    if message_df.is_empty():
        logger.debug(
            f"no existing chat history found for session_id {input.session_id}. Starting a new conversation."
        )
        # This is fresh new session
        # getting the company summary for the given ticker and exchange from cache
        response = await http_client.post(
            "/operation/prompt/search",
            json={
                "prompt": _company_summary_prompt(
                    input.exchange.value, input.ticker
                ),
                "agent": "company-summary",
                "model": settings.app.company_summary_model,  # REVIEW - This is a bit brittle, we should ideally be able to specify the model used for caching at a more granular level instead of hardcoding it here.
                # "cache_tier": "tier2" # TODO - Add support when vector DB is implemented
            },
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company summary not found for {input.ticker} on {input.exchange.value}",
            )
        company_summary = response.json().get("response", "")
        messages = []
        logger.debug(
            f"retrieved company summary from cache for {input.ticker} on {input.exchange.value}"
        )
    else:
        logger.debug(
            f"found existing chat history for session_id {input.session_id}"
        )
        # For existing session, found the previous conversation and use it as context for the QA agent
        company_summary = None
        messages = json_to_history_messages(
            message_df.select(pl.col("message_json")).item()
        )

    agent = company_summary_qa(
        model_name=input.model,
        api_key=settings.get_model_api_keys(input.model),
        company_summary=company_summary,
    )
    async with agent.run_stream(
        input.prompt, message_history=messages
    ) as result:
        async for text in result.stream_text(debounce_by=0.1):
            yield text
    logger.info(f"Completed agent execution for session_id {input.session_id}")

    # Saving the entire conversation till now
    messages_json = history_messages_to_json(result.all_messages())
    chat_history.write(
        pl.DataFrame(
            {
                "session_id": input.session_id,
                "model": input.model,
                "agent": "company-summary-qa",
                "message_json": messages_json,
                "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")),
            }
        ),
        mode="overwrite",
    )
    logger.info(f"Saved chat history for session_id {input.session_id}")
