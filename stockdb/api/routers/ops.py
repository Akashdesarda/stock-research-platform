from datetime import datetime, timedelta
from typing import Annotated

import polars as pl
from deltalake import DeltaTable
from fastapi import APIRouter, HTTPException, Path, status
from fastapi.responses import ORJSONResponse
from pipeline.ticker_history_data_download import download_ticker_history
from stocksense.config import get_settings
from stocksense.data import StockDataDB

from api.models import (
    APITags,
    PromptCacheInput,
    PromptCacheOutput,
    PromptSearchInput,
    StockExchange,
    TaskMode,
    TaskTickerHistoryDownloadInput,
    TickerHistoryDownloadMode,
)

settings = get_settings()

router = APIRouter(prefix="/api/operation", tags=[APITags.ops])


@router.put("/{exchange}/ticker/history")
async def table_optimize_ticker_history(
    exchange: Annotated[
        StockExchange,
        Path(
            description="Symbol of the exchange",
            examples=["nse", "nyse"],
        ),
    ],
    compact: bool = True,
    vacuum: bool = True,
) -> ORJSONResponse:
    """Optimize ticker history table for given exchange
    Optimization includes -
    1. compaction of small files and reorganization of data for better query performance.
    2. vacuuming to remove old data files and free up storage space.
    """
    result = {}
    dt_table = DeltaTable(
        settings.stockdb.data_base_path / f"{exchange.value}/ticker_history"
    )
    if compact:
        compact_result = dt_table.optimize.compact()
        result["compaction"] = compact_result
    if vacuum:
        vacuum_result = dt_table.vacuum(dry_run=False)
        result["vacuum"] = vacuum_result

    return ORJSONResponse(result)


@router.post("/ticker/history")
async def daily_ticker_history_download(task_input: TaskTickerHistoryDownloadInput):
    """Trigger daily ticker history download for all tickers in given exchange"""
    # SECTION 1- Auto mode
    if task_input.task_mode == TaskMode.auto:
        # checking if download is actually needed
        now = datetime.now()
        latest_data_date = (
            now.date() if now.hour >= 18 else now.date() - timedelta(days=1)
        )
        stock_db = StockDataDB(
            settings.stockdb.data_base_path
            / f"{task_input.exchange.value}/ticker_history"
        )
        date_check = (
            await stock_db
            .polars_filter(pl.col("date").max().cast(pl.Date) < latest_data_date)
            .select("close")
            .count()
            .collect_async()
        )

        if date_check.item() == 0:
            # No new data to download
            return {"message": "No new data to download"}
        # Trigger the download task for all tickers in the exchange
        # REVIEW - IF we dont want to wait for result here, then fastapi background task should be used
        # background_tasks.add_task(download_ticker_history, exchange=task_input.exchange)
        if task_input.download_mode == TickerHistoryDownloadMode.incremental:
            result = await download_ticker_history(exchange=task_input.exchange)
            return ORJSONResponse(result)
        if task_input.download_mode == TickerHistoryDownloadMode.full:
            result = await download_ticker_history(
                exchange=task_input.exchange, full_download=True
            )
            return ORJSONResponse(result)

    # SECTION 2 - Manual mode
    elif task_input.task_mode == TaskMode.manual:
        # SECTION 2.1 - Manual mode with full data history download
        if task_input.download_mode == TickerHistoryDownloadMode.full:
            # TODO - implement full download mode
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Full download mode in manual mode is not implemented yet",
            )
            # tickers = [f"{t.symbol}{t.exch_id}" for t in task_input.get_yahoo_aware_ticker()]
            # # background_tasks.add_task(download_entire_ticker_history, task_input.exchange, tickers)
            # data = await download_entire_ticker_history(task_input.exchange, tickers)
        elif task_input.download_mode == TickerHistoryDownloadMode.incremental:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Incremental download mode is not supported in manual mode",
            )
            # SECTION 2.2 - Manual mode with specific date range download
            # tickers = [
            #     f"{t.symbol}{t.exch_id}" for t in task_input.get_yahoo_aware_ticker()
            # ]


@router.post("/prompt/search", response_model=PromptCacheOutput)
async def search_prompt_cache(query: PromptSearchInput) -> ORJSONResponse:
    """Retrieve LLM response from cache"""
    key = query.get_cache_key()
    prompt_cache_table = StockDataDB(
        settings.stockdb.data_base_path / "common/prompt_cache"
    )

    result = await prompt_cache_table.polars_filter(
        (pl.col("prompt_hash") == key)
        & (pl.col("last_modified") + pl.duration(days=pl.col("ttl")) > datetime.now())
    ).collect_async()
    if not result.is_empty():
        return ORJSONResponse(result.select("response", "thinking").to_dicts()[0])
    else:
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": f"No cached response found for the given prompt and '{query.agent}' agent."
            },
        )
    # TODO - Add Tier 2 - Vector DB Storage


@router.put("/prompt/cache")
async def cache_prompt_response(cache_data: PromptCacheInput) -> ORJSONResponse:
    """Store LLM response in cache for future reuse"""
    # Tier 1 - Store in StockDB Delta Table as Hash
    prompt_cache_table = StockDataDB(
        settings.stockdb.data_base_path / "common/prompt_cache"
    )

    current_cache_df = pl.LazyFrame({
        "prompt_hash": cache_data.get_cache_key(),
        "prompt": cache_data.prompt,
        "response": cache_data.response,
        "thinking": cache_data.thinking,
        "agent": cache_data.agent,
        "model": cache_data.model,
        "ttl": cache_data.ttl,
        "last_modified": datetime.now(),
    })

    prompt_cache_table.merge(
        current_cache_df.collect(),
        predicate="s.prompt_hash = t.prompt_hash",
    )

    # TODO - Add Tier 2 - Vector DB Storage

    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Prompt cache stored successfully."},
    )
