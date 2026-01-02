import os

import polars as pl
import pytest
from stocksense.config import get_settings
from stocksense.data import StockDataDB
from stocksense.strategy import TechnicalAnalysis

settings = get_settings(os.getenv("CONFIG_FILE"))


@pytest.fixture(scope="module")
def ta() -> TechnicalAnalysis:
    _ = StockDataDB(settings.stockdb.data_base_path / "nse/ticker_history")
    data = _.sql_filter(
        "select * from stockdb where ticker = 'TCS' order by date desc limit 1000"
    )
    return TechnicalAnalysis(data)


def _has_non_null(df: pl.DataFrame, col: str) -> bool:
    return df.select(col).drop_nulls().height > 0


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
