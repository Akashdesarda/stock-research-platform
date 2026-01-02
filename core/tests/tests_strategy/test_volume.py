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


def test_ad(ta: TechnicalAnalysis):
    result = ta.volume.ad().collect()
    assert "AD" in result.columns
    assert _has_non_null(result, "AD")


def test_adosc(ta: TechnicalAnalysis):
    result = ta.volume.adosc(fastperiod=3, slowperiod=10).collect()
    col = "ADOSC_3_10"
    assert col in result.columns
    assert _has_non_null(result, col)


def test_obv(ta: TechnicalAnalysis):
    result = ta.volume.obv().collect()
    assert "OBV" in result.columns
    assert _has_non_null(result, "OBV")
