import os
import pathlib

import polars as pl
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse
from stocksense.config import get_settings

from api.models import (
    APITags,
    ExchangeTickerInfo,
    StockExchange,
)

settings = get_settings(os.getenv("CONFIG_FILE"))

router = APIRouter(prefix="/api/bulk", tags=[APITags.bulk])


@router.get("/list-tickers", response_model=dict[str, list[ExchangeTickerInfo]])
async def list_exchange_wise_ticker() -> ORJSONResponse:
    """Get all the available `ticker` for all `exchange`"""
    all_exchanges = dict.fromkeys(StockExchange.__members__.keys())

    for exch in all_exchanges:
        table_path: pathlib.Path = settings.stockdb.data_base_path / f"{exch}/equity"
        if not table_path.exists():
            all_exchanges[exch] = None
        else:
            result = await (
                pl.scan_delta(table_path)
                .select(pl.col("symbol").alias("ticker"), "company")
                .sort("ticker")
                .collect_async()
            )
            all_exchanges[exch] = result.to_dicts()

    return ORJSONResponse(all_exchanges)
