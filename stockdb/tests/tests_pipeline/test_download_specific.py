from datetime import date, timedelta
import polars as pl
import pytest
from api.models import StockExchange
from pipeline.ticker_history_data_download import download_specific_date_ticker_history


@pytest.fixture(scope="module")
def nse_tickers() -> list[str]:
    tickers = ["INFY", "TCS", "ABB"]
    tickers.sort()
    return tickers


@pytest.fixture(scope="module")
def nasdaq_tickers() -> list[str]:
    tickers = ["AAPL", "MSFT", "NVDA"]
    tickers.sort()
    return tickers


@pytest.fixture(scope="module")
def nse_ticker_data(nse_tickers) -> pl.LazyFrame:
    return download_specific_date_ticker_history(
        StockExchange.nse,
        nse_tickers,
        date.today() - timedelta(days=5),
    )


@pytest.fixture(scope="module")
def nasdaq_ticker_data(nasdaq_tickers) -> pl.LazyFrame:
    return download_specific_date_ticker_history(
        StockExchange.nasdaq,
        nasdaq_tickers,
        date.today() - timedelta(days=5),
    )


def test_schema(nse_ticker_data):
    assert nse_ticker_data.collect_schema() == pl.Schema(
        {
            "date": pl.Datetime(time_unit="ns", time_zone=None),
            "key": pl.String,
            "ticker": pl.String,
            "open": pl.Float32,
            "high": pl.Float32,
            "low": pl.Float32,
            "close": pl.Float32,
            "volume": pl.UInt64,
        }
    )


# SECTION - NSE
def test_ticker_data_nse(nse_ticker_data):
    assert not nse_ticker_data.select("close").collect().is_empty()


def test_download_date_range_nse(nse_tickers, nse_ticker_data):
    dates = nse_ticker_data.select(
        pl.col("date").min().cast(pl.Date).alias("min_date"),
        pl.col("date").cast(pl.Date).max().alias("max_date"),
    ).collect()

    assert date.today() - timedelta(days=5) <= dates.item(0, "min_date") < date.today()
    assert dates.item(0, "max_date") <= date.today()


def test_ticker_symbol_nse(nse_tickers, nse_ticker_data):
    assert (
        nse_ticker_data.select(pl.col("ticker").unique().sort(descending=False))
        .collect()
        .to_series()
        .to_list()
        == nse_tickers
    )


def test_key_presence_nse(nse_tickers, nse_ticker_data):
    today_key = nse_tickers[1].lower() + str(date.today()).replace("-", "")
    assert (
        today_key
        in nse_ticker_data.filter(pl.col("ticker") == nse_tickers[1])
        .select(pl.col("key"))
        .collect()
        .to_series()
    )


# SECTION - NASDAQ
def test_ticker_data_nasdaq(nasdaq_tickers, nasdaq_ticker_data):
    assert not nasdaq_ticker_data.select("close").collect().is_empty()


def test_ticker_symbol_nasdaq(nasdaq_tickers, nasdaq_ticker_data):
    assert (
        nasdaq_ticker_data.select(pl.col("ticker").unique().sort(descending=False))
        .collect()
        .to_series()
        .to_list()
        == nasdaq_tickers
    )


def test_download_date_range_nasdaq(nasdaq_tickers, nasdaq_ticker_data):
    dates = nasdaq_ticker_data.select(
        pl.col("date").min().cast(pl.Date).alias("min_date"),
        pl.col("date").cast(pl.Date).max().alias("max_date"),
    ).collect()

    assert date.today() - timedelta(days=5) <= dates.item(0, "min_date") < date.today()
    assert dates.item(0, "max_date") <= date.today()


def test_key_presence_nasdaq(nasdaq_tickers, nasdaq_ticker_data):
    today_key = nasdaq_tickers[1].lower() + str(date.today()).replace("-", "")
    assert (
        today_key
        in nasdaq_ticker_data.filter(pl.col("ticker") == nasdaq_tickers[1])
        .select(pl.col("key"))
        .collect()
        .to_series()
    )
