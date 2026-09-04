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


def test_cdldoji_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="pattern",
        method_name="cdldoji",
        output_cols=["CDLDOJI"],
    )


def test_cdlengulfing_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="pattern",
        method_name="cdlengulfing",
        output_cols=["CDLENGULFING"],
    )


def test_cdlabandonedbaby_resets_per_ticker(
    multi_ticker_data: pl.DataFrame,
):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="pattern",
        method_name="cdlabandonedbaby",
        output_cols=["CDLABANDONEDBABY"],
        penetration=0.3,
    )


def test_cdldarkcloudcover_resets_per_ticker(
    multi_ticker_data: pl.DataFrame,
):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="pattern",
        method_name="cdldarkcloudcover",
        output_cols=["CDLDARKCLOUDCOVER"],
        penetration=0.5,
    )


def test_cdldoji(ta: TechnicalAnalysis):
    result = ta.pattern.cdldoji().collect()
    assert "CDLDOJI" in result.columns
    assert _has_non_null(result, "CDLDOJI")


def test_cdlengulfing(ta: TechnicalAnalysis):
    result = ta.pattern.cdlengulfing().collect()
    assert "CDLENGULFING" in result.columns
    assert _has_non_null(result, "CDLENGULFING")


def test_cdlhammer(ta: TechnicalAnalysis):
    result = ta.pattern.cdlhammer().collect()
    assert "CDLHAMMER" in result.columns
    assert _has_non_null(result, "CDLHAMMER")


def test_cdlmorningstar(ta: TechnicalAnalysis):
    result = ta.pattern.cdlmorningstar(penetration=0.3).collect()
    assert "CDLMORNINGSTAR" in result.columns
    assert _has_non_null(result, "CDLMORNINGSTAR")


def test_cdldarkcloudcover(ta: TechnicalAnalysis):
    result = ta.pattern.cdldarkcloudcover(penetration=0.5).collect()
    assert "CDLDARKCLOUDCOVER" in result.columns
    assert _has_non_null(result, "CDLDARKCLOUDCOVER")
