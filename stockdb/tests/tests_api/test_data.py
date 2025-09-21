from datetime import date

import polars as pl
import pytest

from api.data import YFStockData
from api.models import Interval, Period, StockExchangeYahooIdentifier


# SECTION- NSE
@pytest.fixture(scope="module")
def nse_tickers() -> list[str]:
    tickers = ["INFY", "TCS", "ABB"]
    tickers.sort()
    return tickers


@pytest.fixture(scope="module")
def nse_ticker_data(nse_tickers) -> YFStockData:
    return YFStockData(nse_tickers[0], StockExchangeYahooIdentifier.nse)


@pytest.fixture(scope="module")
def nse_tickers_data(nse_tickers) -> YFStockData:
    return YFStockData(nse_tickers, StockExchangeYahooIdentifier.nse)


# SECTION - NASDAQ
@pytest.fixture(scope="module")
def nasdaq_tickers() -> list[str]:
    tickers = ["MSFT", "AAPL", "NVDA"]
    tickers.sort()
    return tickers


@pytest.fixture(scope="module")
def nasdaq_ticker_data(nasdaq_tickers) -> YFStockData:
    return YFStockData(nasdaq_tickers[0], StockExchangeYahooIdentifier.nse)


@pytest.fixture(scope="module")
def nasdaq_tickers_data(nasdaq_tickers) -> YFStockData:
    return YFStockData(nasdaq_tickers, StockExchangeYahooIdentifier.nse)


# SECTION - NSE


def test_nse_ticker_data(nse_tickers, nse_ticker_data):
    assert (
        not nse_ticker_data.get_ticker_history(
            period=Period.FIVE_DAYS, interval=Interval.NINETY_MINUTES
        )[nse_tickers[0]]
        .select("close")
        .is_empty()
    )


def test_nse_tickers_data(nse_tickers_data):
    data = nse_tickers_data.get_ticker_history(
        period=Period.FIVE_DAYS, interval=Interval.NINETY_MINUTES
    )
    for ticker in data:
        assert not data[ticker].select("close").is_empty()


def test_nse_ticker_info(nse_tickers, nse_ticker_data):
    assert (
        nse_ticker_data.yahoo_aware_ticker
        == f"{nse_tickers[0]}{StockExchangeYahooIdentifier.nse.value}"
    )

    info = nse_ticker_data.get_ticker_info()

    assert isinstance(info, dict)
    assert "marketCap" in info[nse_tickers[0]].keys()
    assert "exchange" in info[nse_tickers[0]].keys()
    assert "fiftyTwoWeekHigh" in info[nse_tickers[0]].keys()


def test_nse_tickers_info(nse_tickers_data):
    info = nse_tickers_data.get_ticker_info()
    for ticker in info:
        assert isinstance(info[ticker], dict)
        assert "marketCap" in info[ticker].keys()
        assert "exchange" in info[ticker].keys()
        assert "fiftyTwoWeekHigh" in info[ticker].keys()


def test_nse_ticker_date_range(nse_tickers: list[str], nse_ticker_data: YFStockData):
    sd = date(2025, 9, 10)
    ed = date(2025, 9, 12)
    data = nse_ticker_data.get_ticker_history(start=sd, end=ed)

    assert data[nse_tickers[0]].select(pl.col("date").min()).item().date() == sd, (
        "min date not correct"
    )
    assert data[nse_tickers[0]].select(pl.col("date").max()).item().date() == ed, (
        "max date not correct"
    )


def test_nse_tickers_date_range(nse_tickers_data: YFStockData):
    sd = date(2025, 9, 10)
    ed = date(2025, 9, 12)
    data = nse_tickers_data.get_ticker_history(start=sd, end=ed)

    for ticker in data:
        assert data[ticker].select(pl.col("date").min()).item().date() == sd, (
            "min date not correct"
        )
        assert data[ticker].select(pl.col("date").max()).item().date() == ed, (
            "max date not correct"
        )
