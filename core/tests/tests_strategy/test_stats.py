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


def test_stats_accessor_instantiation(ta: TechnicalAnalysis):
    stats_accessor = ta.stats
    assert stats_accessor is not None


def test_beta_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="stats",
        method_name="beta",
        output_cols=["BETA_5"],
        period=5,
    )


def test_stddev_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="stats",
        method_name="stddev",
        output_cols=["STDDEV_5"],
        period=5,
    )


def test_linearreg(ta: TechnicalAnalysis):
    result = ta.stats.linearreg(period=14)
    col = "LINEARREG_14"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_stddev(ta: TechnicalAnalysis):
    result = ta.stats.stddev(period=5)
    col = "STDDEV_5"
    assert col in result.columns
    assert _has_non_null(result, col)
