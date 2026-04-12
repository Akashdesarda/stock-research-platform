import asyncio
import logging
from datetime import datetime
from typing import AsyncIterable

import polars as pl
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import StreamingResponse
from openinference.semconv.trace import SpanAttributes
from stocksense.ai import track_agent_session
from stocksense.ai.agents import (
    company_summary,
    company_summary_qa,
    text_to_sql,
)
from stocksense.ai.skills.context import (
    CompanyDataContextDependency,
    StockDBContextDependency,
)
from stocksense.ai.utils import (
    get_thinking_parts,
    get_tool_call_parts,
    history_messages_to_json,
    json_to_history_messages,
)
from stocksense.config import get_settings
from stocksense.data import StockDataDB

from api.models import (
    AgentStructuredResponse,
    APITags,
    CompanySummaryAgent,
    CompanySummaryAgentQA,
    PromptCacheInput,
    PromptSearchInput,
    TextToSQLAgent,
)
from api.routers.ops import cache_prompt_response, search_prompt_cache

logger = logging.getLogger("stockdb")
settings = get_settings()


def _company_summary_prompt(exchange: str, ticker: str) -> str:
    return f"Generate a company summary for {ticker} on {exchange} exchange."


# SECTION - FastAPI Router and Endpoints
router = APIRouter(prefix="/api/agent", tags=[APITags.agent])


@router.post("/text-to-sql")
async def text_to_sql_agent(
    input: TextToSQLAgent, background_tasks: BackgroundTasks
) -> AgentStructuredResponse:
    """Agent that converts natural language query to SQL query for stock data"""
    history_data = StockDataDB(
        settings.stockdb.data_base_path
        / f"{input.exchange.value}/ticker_history"
    )
    context = StockDBContextDependency(
        history_data.table_data, table_name=StockDataDB.table_name
    )
    agent = await text_to_sql(
        model_name=input.model,
        api_key=settings.get_model_api_keys(input.model),
        base_url=settings.get_model_base_url(input.model),
    )
    try:
        with track_agent_session(
            name="text-to-sql",
            session_id=input.session_id,
            input_prompt=input.prompt,
            metadata={
                "exchange": input.exchange.value,
                "model": input.model,
            },
        ) as span:
            result = await agent.run(input.prompt, deps=context)
            response = AgentStructuredResponse(
                content=result.output.model_dump(),
                thinking=get_thinking_parts(result.all_messages()),
                tool_calls=get_tool_call_parts(result.all_messages()),
            )

            # Adding info to current span for observability
            span.set_attribute(
                SpanAttributes.OUTPUT_VALUE, result.output.model_dump_json()
            )

        # Persist text-to-sql response as cache
        payload = PromptCacheInput(
            prompt=input.prompt,
            agent="text-to-sql",
            model=input.model,
            response=result.output.sql_query,
            thinking=response.thinking,
            # not setting ttl
        )
        # Offload caching to background task to avoid blocking the API response
        background_tasks.add_task(cache_prompt_response, payload)
        logger.debug(
            f"Scheduled background caching of text-to-sql response for prompt: {input.prompt}"
        )

        return response
    except Exception as e:
        logger.exception(
            "Error occurred in running text-to-sql agent", exc_info=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while running the agent: {str(e)}",
        ) from e


@router.post("/company-summary")
async def company_summary_agent(
    input: CompanySummaryAgent,
    background_tasks: BackgroundTasks,
) -> AgentStructuredResponse:
    """Agent that generates a summary for a given company"""
    prompt = _company_summary_prompt(input.exchange.value, input.ticker)
    context = CompanyDataContextDependency(
        exchange=input.exchange.value,
        ticker=input.ticker,
    )
    agent = await company_summary(
        model_name=input.model,
        api_key=settings.get_model_api_keys(input.model),
        base_url=settings.get_model_base_url(input.model),
    )

    try:
        with track_agent_session(
            name="company-summary",
            session_id=input.session_id,
            input_prompt=prompt,
            metadata={
                "ticker": input.ticker,
                "exchange": input.exchange.value,
                "model": input.model,
            },
        ) as span:
            result = await agent.run(
                # WARNING - The prompt for this agent is fixed and cannot be customized by the user
                # since the agent is specifically designed to generate company summary based on the given ticker and exchange.
                "Give me detail information with respect to the given company data",
                deps=context,
            )
            response = AgentStructuredResponse(
                content=result.output.model_dump(),
                thinking=get_thinking_parts(result.all_messages()),
                tool_calls=get_tool_call_parts(result.all_messages()),
            )

            # Adding info to current span for observability
            span.set_attribute(
                SpanAttributes.OUTPUT_VALUE, result.output.text_output()
            )

        # Persist company summary as cache
        payload = PromptCacheInput(
            prompt=_company_summary_prompt(input.exchange.value, input.ticker),
            agent="company-summary",
            model=input.model,
            response=result.output.text_output(),
            thinking=response.thinking,
            ttl=1,  # Cache for 1 day
        )
        # Offload caching to background task to avoid blocking the API response
        background_tasks.add_task(cache_prompt_response, payload)
        logger.debug(
            f"Scheduled background caching of company summary for {input.ticker} on {input.exchange.value}"
        )

        return response
    except Exception as e:
        logger.exception(
            "Error occurred in running company summary agent", exc_info=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while running the agent: {str(e)}",
        ) from e


@router.post("/company-summary-qa", response_class=StreamingResponse)
async def company_summary_qa_agent(
    input: CompanySummaryAgentQA,
) -> AsyncIterable[str]:
    """Agent that answers questions about a given company based on its summary"""
    # Getting existing conversation history if present
    chat_history = StockDataDB(
        settings.stockdb.data_base_path / "common/chat_history"
    )
    message_df = chat_history.polars_filter(
        pl.col("session_id") == input.session_id
    ).collect()
    if message_df.is_empty():
        logger.debug(
            f"no existing chat history found for session_id: {input.session_id}. Starting a new conversation."
        )
        # This is fresh new session
        try:
            # getting the company summary for the given ticker and exchange from cache
            cache_result = await search_prompt_cache(
                PromptSearchInput(
                    prompt=_company_summary_prompt(
                        input.exchange.value, input.ticker
                    ),
                    agent="company-summary",
                )
            )
            company_summary = cache_result.response
        except HTTPException as e:
            if e.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company summary not found for {input.ticker} on {input.exchange.value}. "
                    f"Please run the company summary agent first to generate the summary.",
                )
            raise e
        messages = []
        logger.debug(
            f"retrieved company summary from cache for {input.ticker} on {input.exchange.value}"
        )
    else:
        logger.debug(
            f"found existing chat history for session_id {input.session_id}"
        )
        # For existing session, found the previous conversation and use it as context for the QA agent
        company_summary = None  # since it will be part of conversation history
        messages = json_to_history_messages(
            message_df.select(pl.col("message_json")).item()
        )

    agent = company_summary_qa(
        model_name=input.model,
        api_key=settings.get_model_api_keys(input.model),
        base_url=settings.get_model_base_url(input.model),
        company_summary=company_summary,
    )

    with track_agent_session(
        name="company-summary-qa",
        session_id=input.session_id,
        input_prompt=input.prompt,
        metadata={
            "ticker": input.ticker,
            "exchange": input.exchange.value,
            "model": input.model,
        },
    ) as span:
        async with agent.run_stream(
            input.prompt, message_history=messages
        ) as result:
            final_text = ""
            async for text in result.stream_text(delta=True, debounce_by=None):
                final_text += text
                yield text

            # Adding info to current span for observability
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, final_text)
    logger.info(f"Completed agent execution for session_id {input.session_id}")

    # Persist the final assistant response alongside streamed deltas.
    messages_for_history = result.all_messages()
    if not messages_for_history or messages_for_history[-1] != result.response:
        messages_for_history.append(result.response)

    # Saving the entire conversation till now
    messages_json = history_messages_to_json(messages_for_history)

    # Offload saving conversation history to a background thread to prevent blocking
    # the async event loop and to allow the generator to yield quickly.
    def save_chat_history():
        chat_history.write(
            pl.DataFrame(
                {
                    "session_id": input.session_id,
                    "model": input.model,
                    "agent": "company-summary-qa",
                    "message_json": messages_json,
                    "timestamp": datetime.now(),
                }
            ),
            mode="overwrite",
        )
        logger.info(f"Saved chat history for session_id {input.session_id}")

    asyncio.create_task(asyncio.to_thread(save_chat_history))
