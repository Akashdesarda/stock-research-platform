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


def test_atr(ta: TechnicalAnalysis):
    result = ta.volatility.atr(period=14).collect()
    col = "ATR_14"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_natr(ta: TechnicalAnalysis):
    result = ta.volatility.natr(period=14).collect()
    col = "NATR_14"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_trange(ta: TechnicalAnalysis):
    result = ta.volatility.trange().collect()
    assert "TRANGE" in result.columns
    assert _has_non_null(result, "TRANGE")
