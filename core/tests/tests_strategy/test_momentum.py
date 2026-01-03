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


def test_rsi(ta: TechnicalAnalysis):
    result = ta.momentum.rsi(period=14).collect()
    assert "RSI_14" in result.columns
    assert _has_non_null(result, "RSI_14")


def test_stochastic(ta: TechnicalAnalysis):
    result = ta.momentum.stochastic().collect()
    assert {"STOCH_slowk", "STOCH_slowd"}.issubset(result.columns)
    assert _has_non_null(result, "STOCH_slowk")
    assert _has_non_null(result, "STOCH_slowd")


def test_cci(ta: TechnicalAnalysis):
    result = ta.momentum.cci(period=20).collect()
    assert "CCI_20" in result.columns
    assert _has_non_null(result, "CCI_20")


def test_roc(ta: TechnicalAnalysis):
    result = ta.momentum.roc(period=10).collect()
    assert "ROC_10" in result.columns
    assert _has_non_null(result, "ROC_10")


def test_momentum(ta: TechnicalAnalysis):
    result = ta.momentum.momentum(period=5).collect()
    assert "MOM_5" in result.columns
    assert _has_non_null(result, "MOM_5")


def test_williams_r(ta: TechnicalAnalysis):
    result = ta.momentum.williams_r(period=14).collect()
    assert "WILLR_14" in result.columns
    assert _has_non_null(result, "WILLR_14")


def test_trix(ta: TechnicalAnalysis):
    result = ta.momentum.trix(period=30).collect()
    assert "TRIX_30" in result.columns
    assert _has_non_null(result, "TRIX_30")


def test_adx(ta: TechnicalAnalysis):
    result = ta.momentum.adx(period=14).collect()
    assert "ADX_14" in result.columns
    assert _has_non_null(result, "ADX_14")


def test_macd(ta: TechnicalAnalysis):
    result = ta.momentum.macd(fastperiod=12, slowperiod=26, signalperiod=9).collect()
    for col in ("MACD", "MACD_signal", "MACD_hist"):
        assert col in result.columns
        assert _has_non_null(result, col)


def test_aroon(ta: TechnicalAnalysis):
    result = ta.momentum.aroon(period=14).collect()
    assert {"AROON_down_14", "AROON_up_14"}.issubset(result.columns)
    assert _has_non_null(result, "AROON_down_14")
    assert _has_non_null(result, "AROON_up_14")


def test_ppo(ta: TechnicalAnalysis):
    result = ta.momentum.ppo(fastperiod=12, slowperiod=26).collect()
    assert "PPO_12_26" in result.columns
    assert _has_non_null(result, "PPO_12_26")


def test_rocr100(ta: TechnicalAnalysis):
    result = ta.momentum.rocr100(period=10).collect()
    assert "ROCR100_10" in result.columns
    assert _has_non_null(result, "ROCR100_10")


def test_stochf(ta: TechnicalAnalysis):
    result = ta.momentum.stochf().collect()
    assert {"STOCHF_fastk", "STOCHF_fastd"}.issubset(result.columns)
    assert _has_non_null(result, "STOCHF_fastk")
    assert _has_non_null(result, "STOCHF_fastd")


def test_ultosc(ta: TechnicalAnalysis):
    result = ta.momentum.ultosc(timeperiod1=7, timeperiod2=14, timeperiod3=28).collect()
    assert "ULTOSC" in result.columns
    assert _has_non_null(result, "ULTOSC")
