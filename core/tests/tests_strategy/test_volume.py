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


def test_ad_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="volume",
        method_name="ad",
        output_cols=["AD"],
    )


def test_adosc_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="volume",
        method_name="adosc",
        output_cols=["ADOSC_3_5"],
        fastperiod=3,
        slowperiod=5,
    )


def test_obv_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="volume",
        method_name="obv",
        output_cols=["OBV"],
    )


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
