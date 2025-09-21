from typing import Annotated


import polars as pl
from fastapi import APIRouter, Depends, Path, Query

from api.config import Settings
from api.dependency.utils import yahoo_finance_aware_ticker
from api.data import YFStockData, StockDataDB
from api.models import (
    APITags,
    ExchangeTickers,
    ExchangeTickersHistory,
    StockExchangeFullName,
    TickerHistoryQuery,
    YahooTickerIdentifier,
    StockExchangeYahooIdentifier,
)

settings = Settings()

nse_history_data = StockDataDB(settings.stockdb.data_base_path / "nse")

router = APIRouter(prefix="/api/per-security", tags=[APITags.per_security])


@router.get("/")
async def list_exchange() -> dict[str, str]:
    """Get list of available exchanges"""
    return {exchange.name.lower(): exchange.value for exchange in StockExchangeFullName}


@router.get("/{exchange}", response_model=ExchangeTickers)
async def list_ticker(
    exchange: Annotated[
        str,
        Path(
            description="Symbol of the exchange",
            examples=["nse", "nyse"],
        ),
    ],
) -> list[str]:
    """Get all the available `ticker` in given `exchange`"""
    return ["INFY", "AAPL"]


@router.get("/{exchange}/{ticker}")
async def ticker_information(
    ticker: Annotated[YahooTickerIdentifier, Depends(yahoo_finance_aware_ticker)],
) -> dict:
    """Get given `Ticker` information"""
    # getting data
    stock_data = YFStockData(
        ticker.symbol, getattr(StockExchangeYahooIdentifier, ticker.exchange.lower())
    )
    result = stock_data.get_ticker_info()
    return result[ticker.symbol]


@router.get("/{exchange}/{ticker}/history")
async def ticker_history(
    ticker: Annotated[YahooTickerIdentifier, Depends(yahoo_finance_aware_ticker)],
    query_param: Annotated[TickerHistoryQuery, Query()],
) -> ExchangeTickersHistory:
    """Get stock history data for given `Ticker`"""
    # 1. first checking local source
    # building the query
    query = [pl.col("ticker") == ticker.symbol.lower()]
    # period condition
    if query_param.period:
        if query_param.period == query_param.period.MAX:
            _ = await nse_history_data.table_data.select(
                pl.col("date").min()
            ).collect_async()
        else:
            _ = await nse_history_data.table_data.select(
                pl.col("date").max()
            ).collect_async()
        latest_available_date = _.item()
        desired_date = (
            pl.Series(latest_available_date)
            .dt.offset_by(query_param.period.value)
            .item()
        )
        query.append(pl.col("date") > desired_date)

    # start date, end date
    if query_param.start_date and query_param.end_date:
        query.append(
            pl.col("date").is_between(query_param.start_date, query_param.end_date)
        )

    # TODO - add for interval

    result = nse_history_data.polars_filter(query)
    # getting data
    # stock_data = YFStockData(
    #     ticker.symbol, getattr(StockExchangeYahooIdentifier, ticker.exchange.lower())
    # )
    # result = stock_data.get_ticker_history(
    #     period=query_param.period,
    #     interval=query_param.interval,
    #     start=query_param.start_date,
    #     end=query_param.end_date,
    # )
    _ = await result.collect_async()
    return ExchangeTickersHistory(
        ticker=ticker.symbol, exchange=ticker.exchange, history=_.to_dicts()
    )
