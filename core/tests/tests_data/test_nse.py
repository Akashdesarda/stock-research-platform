import polars as pl
from stocksense.data import Exchange

exch = Exchange(name="NSE")


def test_get_index_list():
    symbols = exch.nse.get_index_list()

    assert isinstance(symbols, list)

    assert "NIFTY 50" in symbols
    assert "NIFTY BANK" in symbols
    assert "NIFTY IT" in symbols


def test_get_index_quote():
    df = exch.nse.get_index_quote()

    assert not df.is_empty()

    assert "index" in df.columns
    assert "previousClose" in df.columns

    assert df.filter(pl.col("indexSymbol") == "NIFTY MID SELECT").height == 1


def test_get_stock_quote_in_index():
    df = exch.nse.get_stock_quote_in_index("NIFTY 500")

    assert not df.is_empty()

    assert "symbol" in df.columns
    assert "lastPrice" in df.columns

    assert df.filter(pl.col("symbol") == "RELIANCE").height == 1


def test_get_stock_list():
    symbols = exch.nse.get_stock_list()

    assert isinstance(symbols, list)

    assert "RELIANCE" in symbols
    assert "TCS" in symbols
    assert "INFY" in symbols


def test_get_stock_info():
    info = exch.nse.get_stock_info("RELIANCE")

    assert isinstance(info, dict)

    assert list(info.keys()) == [
        "info",
        "metadata",
        "securityInfo",
        "sddDetails",
        "currentMarketType",
        "priceInfo",
        "industryInfo",
        "preOpenMarket",
    ]

    assert info["info"]["companyName"] == "Reliance Industries Limited"
    assert info["industryInfo"]["macro"] == "Energy"


def test_get_index_info():
    info = exch.nse.get_index_info("NIFTY200 ALPHA 30")

    assert isinstance(info, dict)

    assert info["index"] == "NIFTY200 ALPHA 30"
    assert info["previousClose"] >= 10
