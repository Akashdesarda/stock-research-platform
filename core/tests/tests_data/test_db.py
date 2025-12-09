from pathlib import Path

import polars as pl
import pytest
from duckdb import BinderException
from stocksense.data import StockDataDB


@pytest.fixture
def nse_data_db() -> StockDataDB:
    base_dir = Path(Path.home() / "AppData/Roaming/stock-research-platform")
    return StockDataDB(base_dir / "nse/ticker_history")


def test_stock_data_db_init(nse_data_db: StockDataDB):

    assert isinstance(nse_data_db, StockDataDB)
    assert nse_data_db.db_path.exists()
    assert nse_data_db.table_data.count().select("ticker").collect().item() > 0


def test_stock_data_db_sql_filter(nse_data_db: StockDataDB):
    # Simple query
    query = "SELECT * FROM stockdb WHERE ticker = 'RELIANCE' LIMIT 5"
    result = nse_data_db.sql_filter(query).collect()
    assert result.height == 5
    assert all(result["ticker"] == "RELIANCE")

    # Complex query
    query = "SELECT AVG(close) AS avg_closing_price FROM stockdb WHERE ticker = 'TCS' OR ticker = 'INFY' AND date BETWEEN CURRENT_DATE - INTERVAL '1' MONTH AND CURRENT_DATE"
    result = nse_data_db.sql_filter(query).collect()
    assert result.height == 1
    assert "avg_closing_price" in result.columns
    assert result.select("avg_closing_price").item() > 0


def test_stock_data_db_incompatible_sql(nse_data_db: StockDataDB):
    with pytest.raises(BinderException):
        query = "SELECT AVG(close) AS avg_closing_price FROM stockdb WHERE ticker = 'TCS' AND  date BETWEEN DATE_SUB(CURRENT_DATE, INTERVAL 1 MONTH) AND CURRENT_DATE"
        result = nse_data_db.sql_filter(query).collect()


def test_stock_data_db_polars_filter(nse_data_db: StockDataDB):
    # Simple filter
    result = nse_data_db.polars_filter(pl.col("ticker") == "TCS").limit(10).collect()
    assert result.height == 10
    assert all(result["ticker"] == "TCS")

    # Complex filter
    result = (
        nse_data_db.polars_filter(
            (pl.col("ticker") == "INFY") & (pl.col("close") > 1500)
        )
        .limit(7)
        .collect()
    )
    assert result.height == 7
    assert all(result["ticker"] == "INFY")
