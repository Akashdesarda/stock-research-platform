from pathlib import Path

import polars as pl
from api.config import Settings
from api.data import StockDataDB
from deltalake.table import DeltaTable

settings = Settings()


def test_settings():
    assert settings.stockdb.download_batch_size is not None
    assert settings.stockdb.download_batch_size > 0
    assert settings.stockdb.data_base_path.is_dir()


def test_is_delta_table():
    assert DeltaTable.is_deltatable(
        f"{Path(settings.stockdb.data_base_path).as_posix()}/nse/ticker_history"
    )
    assert DeltaTable.is_deltatable(
        f"{Path(settings.stockdb.data_base_path).as_posix()}/nasdaq/ticker_history"
    )


def test_table_schema():
    st_db = StockDataDB(settings.stockdb.data_base_path / "nse/ticker_history")
    s = st_db.table_data.collect_schema()
    assert s["date"] == pl.Datetime
    assert s["company"] == pl.String
    assert s["close"] == pl.Float32
