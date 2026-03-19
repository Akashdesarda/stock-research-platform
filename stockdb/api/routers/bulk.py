from datetime import datetime
from typing import Any

import polars as pl
from duckdb import BinderException, ParserException
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import ORJSONResponse
from stocksense.config import get_settings
from stocksense.data import Exchange, StockDataDB
from stocksense.types import DataInterval, DataPeriod

from api.models import (
    APITags,
    BulkTickerHistoryInput,
    ExchangeTickerInfo,
    StockExchange,
    TickerHistoryOutput,
    TickerQueryInput,
)

settings = get_settings()

router = APIRouter(prefix="/api/bulk", tags=[APITags.bulk])


@router.get("/list-tickers", response_model=dict[str, list[ExchangeTickerInfo] | None])
async def list_exchange_wise_ticker() -> dict:
    """Get all the available `ticker` for all `exchange`"""
    all_exchanges = {}

    for exch in StockExchange:
        table_path = settings.stockdb.data_base_path / f"{exch.value}/equity"
        if not table_path.exists():
            all_exchanges[exch.value] = None
        else:
            result = await (
                pl
                .scan_delta(table_path)
                .select(pl.col("symbol").alias("ticker"), "company")
                .sort("ticker")
                .collect_async()
            )
            all_exchanges[exch.value] = result.to_dicts()

    return ORJSONResponse(all_exchanges)


@router.get("/list-indexes", response_model=dict[str, list[str] | None])
async def list_exchange_wise_indexes() -> ORJSONResponse:
    """Get all the available `index_symbol` for all `exchange`"""
    exch = Exchange()
    all_exchanges = {}

    for exch_name in StockExchange:
        try:
            exch_accessor = getattr(exch, exch_name.value.lower())
            all_exchanges[exch_name.value] = exch_accessor.get_index_list()
        # NOTE - Some exchanges may not have index info implemented. So there won't be any accessor
        # property for those exchanges in `Exchange` class.
        except AttributeError:
            all_exchanges[exch_name.value] = None

    return ORJSONResponse(all_exchanges)


@router.post("/ticker/query", response_model=list[dict[str, Any]])
async def ticker_query(input_body: TickerQueryInput) -> list[dict[str, Any]]:
    """Get stock history data for given `exchange` using SQL query"""
    history_data = StockDataDB(
        settings.stockdb.data_base_path / f"{input_body.exchange.value}/ticker_history"
    )
    # Execute SQL query
    try:
        result = history_data.sql_filter(input_body.sql_query).with_columns(
            pl.col(pl.Decimal).cast(pl.Float64)
        )
        result = await result.collect_async()
        return result.to_dicts()
    except (BinderException, ParserException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/ticker/history", response_model=list[TickerHistoryOutput])
async def ticker_history(input_body: BulkTickerHistoryInput) -> list[dict]:
    """Get stock history data for given `exchange` using SQL query"""
    history_data = StockDataDB(
        settings.stockdb.data_base_path / f"{input_body.exchange.value}/ticker_history"
    )
    # getting all the tickers as upper case
    tickers = [t.upper() for t in input_body.ticker]

    # Building the query
    # 1. ticker condition
    query = [pl.col("ticker").is_in(tickers)]
    # 2. start & end condition
    if input_body.start_date is not None:
        query.append(
            pl.col("date").is_between(input_body.start_date, input_body.end_date)
        )
    # 3. Period condition
    elif input_body.period:
        query.append(
            pl.col("date")
            >= (
                pl.col("date").min()
                if input_body.period == DataPeriod.MAX
                else pl.datetime(datetime.now().year, 1, 1)
                if input_body.period == DataPeriod.YEAR_TO_DATE
                else pl.col("date").max().dt.offset_by(f"-{input_body.period.value}")
            )
        )
    result = history_data.polars_filter(query)
    # 4. Interval condition
    if input_body.interval not in {
        DataInterval.ONE_DAY,
        DataInterval.FIVE_DAYS,
        DataInterval.ONE_WEEK,
        DataInterval.ONE_MONTH,
        DataInterval.THREE_MONTHS,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interval less than 1 day is not supported",
        )
    # NOTE - Normalize interval value for '1w'/'1wk'
    interval_value = input_body.interval.value
    if interval_value == "1wk":
        interval_value = "1w"

    result = (
        result
        .sort([
            "ticker",
            "date",
        ])  # dynamic grouping requires ascending data within each ticker
        .group_by_dynamic(
            index_column="date",
            group_by="ticker",
            every=interval_value,
            start_by="datapoint",  # grouping should start from first data point
            # aggregation is done by simply taking all value from group; then taking first value from each
        )
        .agg(pl.all().first())
        .select(
            "date",
            "ticker",
            "company",
            "open",
            "high",
            "low",
            "close",
            "volume",
        )
        .sort("date", descending=True)  # sorting back to latest date first
    )

    result = await result.collect_async()  # ty:ignore[invalid-await]
    return result.to_dicts()
