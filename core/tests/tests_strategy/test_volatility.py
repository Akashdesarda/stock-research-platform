import polars as pl
import pytest
from helpers.grouped import (
    assert_grouped_matches_single_ticker,
    make_multi_ticker_data,
)
from stocksense.config import get_settings
from stocksense.data import StockDataDB
from stocksense.strategy import TechnicalAnalysis

settings = get_settings()


@pytest.fixture(scope="module")
def ta() -> TechnicalAnalysis:
    _ = StockDataDB(settings.stockdb.data_base_path / "nse/ticker_history")
    data = _.sql_filter(
        "select * from stockdb where ticker = 'TCS' order by date desc limit 1000"
    )
    return TechnicalAnalysis(data, group_by="ticker", sort_by="date")


def _has_non_null(df: pl.DataFrame, col: str) -> bool:
    return df.select(col).drop_nulls().height > 0


@pytest.fixture
def multi_ticker_data() -> pl.DataFrame:
    return make_multi_ticker_data()


def test_atr_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="volatility",
        method_name="atr",
        output_cols=["ATR_5"],
        period=5,
    )


def test_natr_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="volatility",
        method_name="natr",
        output_cols=["NATR_5"],
        period=5,
    )


def test_trange_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="volatility",
        method_name="trange",
        output_cols=["TRANGE"],
    )


def test_atr(ta: TechnicalAnalysis):
    result = ta.volatility.atr(period=14)
    col = "ATR_14"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_natr(ta: TechnicalAnalysis):
    result = ta.volatility.natr(period=14)
    col = "NATR_14"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_trange(ta: TechnicalAnalysis):
    result = ta.volatility.trange()
    assert "TRANGE" in result.columns
    assert _has_non_null(result, "TRANGE")
