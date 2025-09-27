from typing import Annotated, Any

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import ORJSONResponse

from api.config import Settings
from api.data import StockDataDB, YFStockData
from api.dependency.utils import yahoo_finance_aware_ticker
from api.models import (
    APITags,
    Interval,
    Period,
    StockExchange,
    StockExchangeFullName,
    StockExchangeYahooIdentifier,
    TickerHistoryOutput,
    TickerHistoryQuery,
    YahooTickerIdentifier,
)

settings = Settings()

router = APIRouter(prefix="/api/per-security", tags=[APITags.per_security])


@router.get("/")
async def list_exchange() -> dict[str, str]:
    """Get list of available exchanges"""
    return {exchange.name.lower(): exchange.value for exchange in StockExchangeFullName}


@router.get("/{exchange}")
async def list_ticker(
    exchange: Annotated[
        StockExchange,
        Path(
            description="Symbol of the exchange",
            examples=["nse", "nyse"],
        ),
    ],
    # REVIEW - Should I add more exchange info?
) -> list[str]:
    """Get all the available `ticker` in given `exchange`"""
    result = await (
        pl.scan_delta(settings.stockdb.data_base_path / "common/security")
        .select(exchange.value)
        .explode(exchange.value)
        .sort(exchange.value)
        .collect_async()
    )
    return result.to_series().to_list()


@router.get("/{exchange}/{ticker}")
async def ticker_information(
    ticker: Annotated[YahooTickerIdentifier, Depends(yahoo_finance_aware_ticker)],
) -> dict[str, Any]:
    """Get given `Ticker` information"""
    # getting data
    stock_data = YFStockData(
        ticker.symbol, getattr(StockExchangeYahooIdentifier, ticker.exchange.lower())
    )
    result = stock_data.get_ticker_info()
    return result[ticker.symbol]


@router.get("/{exchange}/{ticker}/history", response_model=TickerHistoryOutput)
async def ticker_history(
    ticker: Annotated[YahooTickerIdentifier, Depends(yahoo_finance_aware_ticker)],
    query_param: Annotated[TickerHistoryQuery, Query()],
) -> ORJSONResponse:
    """Get stock history data for given `Ticker`"""
    nse_history_data = StockDataDB(
        settings.stockdb.data_base_path / f"{ticker.exchange.lower()}/ticker_history"
    )
    # Building the query
    query = [pl.col("ticker") == ticker.symbol]
    # start & end condition
    if query_param.start_date is not None:
        query.append(
            pl.col("date").is_between(query_param.start_date, query_param.end_date)
        )
    # 1. Period condition
    elif query_param.period:
        if query_param.period == Period.MAX:
            query.append(pl.col("date") >= pl.col("date").min())
        elif query_param.period == Period.YEAR_TO_DATE:
            query.append(pl.col("date") >= pl.datetime(pl.date.today().year, 1, 1))
        else:
            query.append(
                pl.col("date")
                >= pl.col("date").max().dt.offset_by(f"-{query_param.period.value}")
            )
    result = nse_history_data.polars_filter(query)

    # 2. Interval condition
    if query_param.interval not in (
        Interval.ONE_DAY,
        Interval.FIVE_DAYS,
        Interval.ONE_WEEK,
        Interval.ONE_MONTH,
        Interval.THREE_MONTHS,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interval less than 1 day is not supported",
        )
    result = (
        result.sort("date")
        .group_by_dynamic(
            index_column="date",
            every=query_param.interval.value,
            start_by="datapoint",  # grouping should start from first data point
            # aggregation is done by simply taking all value from group; then taking first value from each
        )
        .agg(pl.all().first())
    )

    result = result.select(
        "date", "ticker", "company", "open", "high", "low", "close", "volume"
    )

    result = await result.collect_async()
    return ORJSONResponse(result.to_dicts())
