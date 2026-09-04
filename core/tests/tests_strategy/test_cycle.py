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


def test_ht_dcperiod_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="cycle",
        method_name="ht_dcperiod",
        output_cols=["HT_DCPERIOD"],
    )


def test_ht_dcphase_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="cycle",
        method_name="ht_dcphase",
        output_cols=["HT_DCPHASE"],
    )


def test_ht_phasor_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="cycle",
        method_name="ht_phasor",
        output_cols=["HT_PHASOR_inphase", "HT_PHASOR_quadrature"],
    )


def test_ht_sine_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="cycle",
        method_name="ht_sine",
        output_cols=["HT_SINE", "HT_LEADSINE"],
    )


def test_ht_trendmode_resets_per_ticker(multi_ticker_data: pl.DataFrame):
    assert_grouped_matches_single_ticker(
        multi_ticker_data,
        accessor_name="cycle",
        method_name="ht_trendmode",
        output_cols=["HT_TRENDMODE"],
    )


def test_ht_dcperiod(ta: TechnicalAnalysis):
    result = ta.cycle.ht_dcperiod().collect()
    assert "HT_DCPERIOD" in result.columns
    assert _has_non_null(result, "HT_DCPERIOD")


def test_ht_dcphase(ta: TechnicalAnalysis):
    result = ta.cycle.ht_dcphase().collect()
    assert "HT_DCPHASE" in result.columns
    assert _has_non_null(result, "HT_DCPHASE")


def test_ht_phasor(ta: TechnicalAnalysis):
    result = ta.cycle.ht_phasor().collect()
    assert {"HT_PHASOR_inphase", "HT_PHASOR_quadrature"}.issubset(
        result.columns
    )
    assert _has_non_null(result, "HT_PHASOR_inphase")
    assert _has_non_null(result, "HT_PHASOR_quadrature")


def test_ht_sine(ta: TechnicalAnalysis):
    result = ta.cycle.ht_sine().collect()
    assert {"HT_SINE", "HT_LEADSINE"}.issubset(result.columns)
    assert _has_non_null(result, "HT_SINE")
    assert _has_non_null(result, "HT_LEADSINE")


def test_ht_trendmode(ta: TechnicalAnalysis):
    result = ta.cycle.ht_trendmode().collect()
    assert "HT_TRENDMODE" in result.columns
    assert _has_non_null(result, "HT_TRENDMODE")
