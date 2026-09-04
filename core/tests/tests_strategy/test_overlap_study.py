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


def test_bbands_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="overlap",
        method_name="bbands",
        output_cols=["BBANDS_upper_5", "BBANDS_middle_5", "BBANDS_lower_5"],
        period=5,
        nbdevup=2.0,
        nbdevdn=2.0,
    )


def test_ema_with_runtime_col_resets_per_ticker(
    multi_ticker_data: pl.DataFrame,
):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="overlap",
        method_name="ema",
        output_cols=["EMA_5"],
        period=5,
        col="adjusted_close",
    )


def test_sar_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="overlap",
        method_name="sar",
        output_cols=["SAR"],
        acceleration=0.02,
        maximum=0.2,
    )


def test_t3_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="overlap",
        method_name="t3",
        output_cols=["T3_5_0_7"],
        period=5,
        vfactor=0.7,
    )


def test_ht_trendline_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="overlap",
        method_name="ht_trendline",
        output_cols=["HT_TRENDLINE"],
    )


def test_bbands(ta: TechnicalAnalysis):
    result = ta.overlap.bbands(period=20, nbdevup=2.0, nbdevdn=2.0).collect()
    cols = {"BBANDS_upper_20", "BBANDS_middle_20", "BBANDS_lower_20"}
    assert cols.issubset(result.columns)
    for c in cols:
        assert _has_non_null(result, c)


def test_ema(ta: TechnicalAnalysis):
    result = ta.overlap.ema(period=30).collect()
    col = "EMA_30"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_sma(ta: TechnicalAnalysis):
    result = ta.overlap.sma(period=15).collect()
    col = "SMA_15"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_kama(ta: TechnicalAnalysis):
    result = ta.overlap.kama(period=30).collect()
    col = "KAMA_30"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_sar(ta: TechnicalAnalysis):
    result = ta.overlap.sar(acceleration=0.02, maximum=0.2).collect()
    assert "SAR" in result.columns
    assert _has_non_null(result, "SAR")


def test_t3(ta: TechnicalAnalysis):
    result = ta.overlap.t3(period=5, vfactor=0.7).collect()
    col = "T3_5_0_7"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_wma(ta: TechnicalAnalysis):
    result = ta.overlap.wma(period=20).collect()
    col = "WMA_20"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_dema(ta: TechnicalAnalysis):
    result = ta.overlap.dema(period=25).collect()
    col = "DEMA_25"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_ht_trendline(ta: TechnicalAnalysis):
    result = ta.overlap.ht_trendline().collect()
    assert "HT_TRENDLINE" in result.columns
    assert _has_non_null(result, "HT_TRENDLINE")
