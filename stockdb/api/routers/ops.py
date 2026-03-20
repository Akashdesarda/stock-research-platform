from base64 import b64encode
from datetime import datetime, timedelta
from typing import Annotated

import polars as pl
from deltalake import DeltaTable
from fastapi import APIRouter, HTTPException, Path, status
from pipeline.ticker_history_data_download import download_ticker_history
from stocksense.config import get_settings
from stocksense.data import StockDataDB

from api.models import (
    APITags,
    DataRegistrationInput,
    LogicalPlan,
    PromptCacheInput,
    PromptCacheOutput,
    PromptSearchInput,
    RegisteredDataOutput,
    StockExchange,
    TaskMode,
    TaskTickerHistoryDownloadInput,
    TickerHistoryDownloadMode,
)
from api.routers import _build_history_lf_from_query, _logical_plan_to_lf

settings = get_settings()

router = APIRouter(prefix="/api/operation", tags=[APITags.ops])


@router.put("/optimize/{exchange}/ticker/history")
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
) -> dict:
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

    return result


@router.post("/download/ticker/history")
async def daily_ticker_history_download(
    task_input: TaskTickerHistoryDownloadInput,
) -> dict | None:
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
            return result
        if task_input.download_mode == TickerHistoryDownloadMode.full:
            result = await download_ticker_history(
                exchange=task_input.exchange, full_download=True
            )
            return result

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


@router.post("/prompt/search")
async def search_prompt_cache(query: PromptSearchInput) -> PromptCacheOutput:
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
        return PromptCacheOutput(**result.select("response", "thinking").to_dicts()[0])
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cached response found for the given prompt and '{query.agent}' agent.",
        )
    # TODO - Add Tier 2 - Vector DB Storage


@router.put("/prompt/cache", status_code=status.HTTP_201_CREATED)
async def cache_prompt_response(cache_data: PromptCacheInput) -> dict:
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
    return {"message": "Prompt cache stored successfully"}


@router.get("/data", response_model=list[RegisteredDataOutput])
async def list_registered_data() -> list[dict]:
    """List all registered data"""
    registered_data = StockDataDB(
        settings.stockdb.data_base_path / "common/registered_data"
    )
    result = await registered_data.table_data.collect_async()
    return result.to_dicts()


@router.get("/data/{dataset_id}", response_model=RegisteredDataOutput)
async def get_registered_data(dataset_id: str) -> dict:
    """Retrieve registered data based on dataset_id"""
    registered_data = StockDataDB(
        settings.stockdb.data_base_path / "common/registered_data"
    )
    result = await registered_data.polars_filter(
        pl.col("dataset_id") == dataset_id
    ).collect_async()

    if not result.is_empty():
        return result.to_dicts()[0]
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered data found for dataset_id: {dataset_id}",
        )


@router.get("/data/{dataset_id}/serialize")
async def get_registered_data_bytes(dataset_id: str) -> str:
    """Retrieve registered data as polars lazyframe serialized into base64 string based"""
    registered_data = StockDataDB(
        settings.stockdb.data_base_path / "common/registered_data"
    )
    result = (
        await registered_data
        .polars_filter(pl.col("dataset_id") == dataset_id)
        .select("logical_plan")
        .collect_async()
    )

    if result.is_empty():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered data found for dataset_id: {dataset_id}",
        )
    logical_plan_dict = result.select(
        "logical_plan"
    ).item()  # to_dicts()[0]["logical_plan"]
    logical_plan = LogicalPlan.model_validate(logical_plan_dict)
    lf = _logical_plan_to_lf(logical_plan)

    return b64encode(lf.serialize()).decode("utf-8")


@router.post("/data/hydrate")
async def hydrate_registered_data(plan: LogicalPlan) -> list[dict]:
    """Hydrate & return registered data based on the logical plan provided in the request body"""
    result = await _logical_plan_to_lf(plan).collect_async()

    return result.to_dicts()


@router.put("/data/register", status_code=status.HTTP_201_CREATED)
async def register_data(register: DataRegistrationInput):
    """Store OHLC data that can be used running all kinds of quantitative and qualitative analysis"""

    # Verifying if logical plan is valid by trying to parse it using polars.
    sdb = StockDataDB(
        settings.stockdb.data_base_path
        / f"{register.logical_plan.exchange.value}/ticker_history"
    )
    # 1st priority to sql query
    if register.logical_plan.sql_query:
        df = sdb.sql_filter(register.logical_plan.sql_query)
    # 2nd priority to logical plan serialized in bytes
    else:
        try:
            df = _build_history_lf_from_query(
                data=sdb,
                ticker=register.logical_plan.ticker,
                start_date=register.logical_plan.start_date,
                end_date=register.logical_plan.end_date,
                period=register.logical_plan.period,
                interval=register.logical_plan.interval,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

    if df.limit(1).collect().is_empty():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid logical plan provided. Please ensure the logical plan is correctly serialized and represents a valid Polars LazyFrame.",
        )

    registered_data = StockDataDB(
        settings.stockdb.data_base_path / "common/registered_data"
    )
    current_data_df = pl.DataFrame(
        [
            {
                "dataset_id": register.dataset_id,
                "name": register.name,
                "description": register.description,
                "logical_plan": register.logical_plan.model_dump(mode="json"),
                "tags": register.tags,
                "last_modified": datetime.now(),
            }
        ],
        schema_overrides={
            "logical_plan": pl.Struct({
                "exchange": pl.String,
                "ticker": pl.List(pl.String),
                "interval": pl.String,
                "period": pl.String,
                "start_date": pl.Date,
                "end_date": pl.Date,
                "sql_query": pl.String,
            }),
            "tags": pl.List(pl.String),
        },
    )
    # .with_columns(pl.col("tags").cast(pl.List(pl.String)))

    # Merging on dataset_id
    registered_data.merge(current_data_df, predicate="s.dataset_id = t.dataset_id")
    return {"message": "Data registered successfully"}
