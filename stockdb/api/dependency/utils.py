from typing import Annotated

from fastapi import Body, HTTPException, Path, status

from api.models import (
    StockExchange,
    StockExchangeYahooIdentifier,
    YahooTickerIdentifier,
)


async def yahoo_finance_aware_ticker(
    exchange: Annotated[
        StockExchange,
        Path(
            description="Exchange symbol to which `Ticker` belongs",
        ),
    ],
    ticker: Annotated[str, Path(description="Desired company's `Ticker` symbol")],
) -> YahooTickerIdentifier:
    """Dependency to get Yahoo Finance aware ticker symbol"""
    ticker = ticker.upper()  # making sure that ticker symbol are always Upper case
    return YahooTickerIdentifier(
        symbol=ticker,
        exchange=exchange.name.upper(),
        exch_id=getattr(StockExchangeYahooIdentifier, exchange.name),
    )


async def yahoo_finance_aware_exchange_check(
    exchange: Annotated[
        list,
        Body(
            embed=True,
            description="List of desired exchanges of which tickers are needed to be fetched",
            examples=[["NSE", "BSE", "NYSE"], ["TSO", "LSO", "BSE"]],
        ),
    ],
):
    """Dependency to get Yahoo Finance aware exchange"""
    exchange_name = {exch.name for exch in StockExchange}
    diff = list(set(exchange).difference(exchange_name))
    if diff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The following exchanges are not supported: {diff}",
        )
    return exchange
