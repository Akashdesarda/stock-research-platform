import logging
import os

import deltalake
import polars as pl
from api.models import StockExchange
from deltalake.table import DeltaTable
from stocksense.config import get_settings

logger = logging.getLogger("stockdb")
settings = get_settings(os.getenv("CONFIG_FILE"))

ticker_history = pl.DataFrame(
    schema={
        "date": pl.Datetime,
        "ticker": pl.String,
        "company": pl.String,
        "open": pl.Float32,
        "high": pl.Float32,
        "low": pl.Float32,
        "close": pl.Float32,
        "volume": pl.Int64,
    }
)

# Creating ticker history table for all exchange
for exchange in StockExchange:
    logger.info(f"Creating table for {exchange.name}")
    ticker_history.write_delta(
        settings.stockdb.data_base_path / f"{exchange.value}/ticker_history",
        mode="overwrite",
        delta_write_options={
            "writer_properties": deltalake.WriterProperties(
                compression="ZSTD", compression_level=5
            ),
            "schema_mode": "overwrite",
        },
    )
    dt = DeltaTable(
        settings.stockdb.data_base_path / f"{exchange.value}/ticker_history"
    )
    dt.optimize.z_order(["date", "ticker", "company"])
    logger.info(f"Finished creating table & z-ordering for {exchange.name}")
