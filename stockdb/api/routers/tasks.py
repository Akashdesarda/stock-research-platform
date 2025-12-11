from datetime import datetime, timedelta

import polars as pl
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import ORJSONResponse
from pipeline.ticker_history_data_download import download_ticker_history
from stocksense.data import StockDataDB

from api.config import Settings
from api.models import (
    APITags,
    TaskMode,
    TaskTickerHistoryDownloadInput,
    TickerHistoryDownloadMode,
)

settings = Settings()

router = APIRouter(prefix="/api/task", tags=[APITags.task])


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
            await stock_db.polars_filter(
                pl.col("date").max().cast(pl.Date) < latest_data_date
            )
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
        # TODO - implement full download mode
        if task_input.download_mode == TickerHistoryDownloadMode.full:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Full download mode in auto mode is not implemented yet",
            )

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
