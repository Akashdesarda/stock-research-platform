from datetime import date, timedelta
import polars as pl
import pytest
from api.models import StockExchange
from pipeline.ticker_history_data_download import download_entire_ticker_history


@pytest.fixture(scope="module")
def tickers() -> list[str]:
    tickers = ["INFY", "TCS", "ABB"]
    tickers.sort()
    return tickers


@pytest.fixture(scope="module")
def ticker_data(tickers) -> pl.LazyFrame:
    return download_entire_ticker_history(StockExchange.nse, tickers)


def test_schema(ticker_data):
    assert ticker_data.collect_schema() == pl.Schema(
        {
            "date": pl.Datetime(time_unit="ns", time_zone=None),
            "key": pl.String,
            "ticker": pl.String,
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Float64,
        }
    )


def test_download_initial_date(tickers, ticker_data):
    dates = (
        ticker_data.group_by("ticker").agg(
            pl.col("date").min().cast(pl.Date).alias("min_date")
        )
        # .collect()
    )

    assert dates.filter(pl.col("ticker") == tickers[0]).collect().item(
        0, "min_date"
    ) == date(2002, 7, 1)
    assert dates.filter(pl.col("ticker") == tickers[1]).collect().item(
        0, "min_date"
    ) == date(1996, 1, 1)
    assert dates.filter(pl.col("ticker") == tickers[2]).collect().item(
        0, "min_date"
    ) == date(2002, 8, 12)


def test_ticker_symbol(tickers, ticker_data):
    assert (
        ticker_data.select(pl.col("ticker").unique().sort(descending=False))
        .collect()
        .to_series()
        .to_list()
        == tickers
    )


def test_key_presence(tickers, ticker_data):
    today_key = tickers[1].lower() + str(date.today() - timedelta(days=1)).replace(
        "-", ""
    )
    assert (
        today_key
        in ticker_data.filter(pl.col("ticker") == tickers[1])
        .select(pl.col("key"))
        .collect()
        .to_series()
    )
