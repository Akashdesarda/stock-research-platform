import pytest
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
    return TechnicalAnalysis(data)


def test_trend_sma(ta: TechnicalAnalysis):
    result = ta.trend.sma(period=15).collect()
    assert "SMA_15" in result.columns
    assert result.select("SMA_15").drop_nulls().height > 0


def test_trend_sma_crossover(ta: TechnicalAnalysis):
    result = ta.trend.sma_crossover(fast=5, slow=10).collect()
    cols = result.columns
    assert "SMA_5" in cols
    assert "SMA_10" in cols
    assert "SMA_crossover_5_10" in cols
    assert result.select("SMA_5").drop_nulls().height > 0
    assert result.select("SMA_10").drop_nulls().height > 0
    assert result["SMA_crossover_5_10"].is_in([True, False]).all()


def test_trend_ema_crossover(ta: TechnicalAnalysis):
    result = ta.trend.ema_crossover(fast=12, slow=26).collect()
    cols = result.columns
    assert "EMA_12" in cols
    assert "EMA_26" in cols
    assert "EMA_crossover_12_26" in cols
    assert result.select("EMA_12").drop_nulls().height > 0
    assert result.select("EMA_26").drop_nulls().height > 0


def test_trend_macd(ta: TechnicalAnalysis):
    result = ta.trend.macd(fastperiod=12, slowperiod=26, signalperiod=9).collect()
    cols = result.columns
    assert "MACD" in cols
    assert "MACD_signal" in cols
    assert "MACD_hist" in cols
    assert result.select("MACD").drop_nulls().height > 0


def test_trend_adx_dmi(ta: TechnicalAnalysis):
    result = ta.trend.adx_dmi(period=14).collect()
    cols = result.columns
    assert "ADX_14" in cols
    assert "DI_plus_14" in cols
    assert "DI_minus_14" in cols
    assert result.select("ADX_14").drop_nulls().height > 0


def test_trend_parabolic_sar(ta: TechnicalAnalysis):
    result = ta.trend.parabolic_sar(acceleration=0.02, maximum=0.2).collect()
    cols = result.columns
    assert "SAR" in cols
    assert result.select("SAR").drop_nulls().height > 0


def test_trend_kama(ta: TechnicalAnalysis):
    result = ta.trend.kama(period=30).collect()
    cols = result.columns
    assert "KAMA_30" in cols
    assert result.select("KAMA_30").drop_nulls().height > 0


def test_trend_t3(ta: TechnicalAnalysis):
    result = ta.trend.t3(period=5, vfactor=0.7).collect()
    cols = result.columns
    assert "T3_5_0_7" in cols
    assert result.select("T3_5_0_7").drop_nulls().height > 0
