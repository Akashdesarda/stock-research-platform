from datetime import datetime

import polars as pl
import pytest
from stocksense.data import Exchange
from stocksense.data._nse import NSEAccessor


@pytest.fixture(scope="module")
def nse() -> NSEAccessor:
    return Exchange().nse


# SECTION - Facade wiring
# `stockdb/api/routers/bulk.py` reaches the accessor via `getattr(exch, "nse")`
# and swallows AttributeError, so a rename would silently break /list-indexes.


def test_exchange_nse_accessor():
    exch = Exchange()
    assert isinstance(exch.nse, NSEAccessor)

    for method in (
        "get_stock_list",
        "get_stock_info",
        "get_index_list",
        "get_index_info",
        "get_index_quote",
        "get_stock_quote_in_index",
    ):
        assert callable(getattr(exch.nse, method)), f"missing NSE method {method!r}"


# SECTION - Stock list


def test_get_stock_list(nse: NSEAccessor):
    symbols = nse.get_stock_list()

    assert isinstance(symbols, list)
    assert all(isinstance(s, str) for s in symbols)
    # Symbols must be bare (no ".NS"/".BO" suffix) — stockdb appends the suffix itself.
    assert all("." not in s for s in symbols[:100])
    assert len(symbols) == len(set(symbols)), "stock list should have no duplicates"

    for expected in ("RELIANCE", "TCS", "INFY"):
        assert expected in symbols


# SECTION - Stock info
# Pins the exact fields consumed by `stockdb/pipeline/exchange_equity_tableinfo.py`,
# so a library swap that reshapes the payload fails here rather than in prod.


def test_get_stock_info_top_level_keys(nse: NSEAccessor):
    info = nse.get_stock_info("RELIANCE")

    assert isinstance(info, dict)
    # Subset check (not exact match) — NSE occasionally adds fields, we only care
    # that the ones stockdb reads are present.
    required = {"info", "metadata", "priceInfo", "industryInfo"}
    assert required.issubset(info.keys()), (
        f"missing required keys: {required - info.keys()}"
    )


def test_get_stock_info_info_section(nse: NSEAccessor):
    info = nse.get_stock_info("RELIANCE")["info"]

    assert info["symbol"] == "RELIANCE"
    assert info["companyName"] == "Reliance Industries Limited"


def test_get_stock_info_metadata_pipeline_contract(nse: NSEAccessor):
    """Fields consumed by exchange_equity_tableinfo.py."""
    metadata = nse.get_stock_info("RELIANCE")["metadata"]

    # listingDate must parse as "%d-%b-%Y" (e.g. "29-Nov-1995")
    listing_date = metadata["listingDate"]
    assert isinstance(listing_date, str)
    datetime.strptime(listing_date, "%d-%b-%Y")

    # pdSectorIndAll is either a comma-separated string or a list of index names.
    sector_ind = metadata["pdSectorIndAll"]
    assert isinstance(sector_ind, (str, list))

    assert isinstance(metadata["series"], str) and metadata["series"]


def test_get_stock_info_industry_info(nse: NSEAccessor):
    industry = nse.get_stock_info("RELIANCE")["industryInfo"]
    assert industry["macro"] == "Energy"


def test_get_stock_info_invalid_ticker(nse: NSEAccessor):
    """Invalid tickers must either raise or return a payload without `info`.

    The stockdb pipeline guards on a missing `info` key, so both failure modes
    are acceptable. This locks that contract in against library swaps.
    """
    try:
        result = nse.get_stock_info("__DEFINITELY_NOT_A_REAL_TICKER__")
    except Exception:
        return
    assert not result or not result.get("info"), (
        f"invalid ticker returned a valid-looking payload: {result!r}"
    )


# SECTION - Index list


def test_get_index_list(nse: NSEAccessor):
    symbols = nse.get_index_list()

    assert isinstance(symbols, list)
    assert all(isinstance(s, str) for s in symbols)

    for expected in ("NIFTY 50", "NIFTY BANK", "NIFTY IT"):
        assert expected in symbols


# SECTION - Index info


def test_get_index_info(nse: NSEAccessor):
    info = nse.get_index_info("NIFTY200 ALPHA 30")

    assert isinstance(info, dict)
    assert info["index"] == "NIFTY200 ALPHA 30"
    assert isinstance(info["previousClose"], (int, float))
    assert info["previousClose"] > 0


# SECTION - Index quote (all indices)


def test_get_index_quote(nse: NSEAccessor):
    df = nse.get_index_quote()

    assert isinstance(df, pl.DataFrame)
    assert not df.is_empty()

    for col in ("index", "indexSymbol", "previousClose"):
        assert col in df.columns

    assert df.schema["previousClose"].is_numeric()
    assert df.filter(pl.col("indexSymbol") == "NIFTY MID SELECT").height == 1


# SECTION - Stock quotes within an index


def test_get_stock_quote_in_index(nse: NSEAccessor):
    df = nse.get_stock_quote_in_index("NIFTY 500")

    assert isinstance(df, pl.DataFrame)
    assert not df.is_empty()

    for col in ("symbol", "lastPrice"):
        assert col in df.columns

    assert df.schema["lastPrice"].is_numeric()
    assert df.filter(pl.col("symbol") == "RELIANCE").height == 1
