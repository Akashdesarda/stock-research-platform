import os

import polars as pl
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse
from stocksense.config import get_settings
from stocksense.data import Exchange

from api.models import (
    APITags,
    ExchangeTickerInfo,
    StockExchange,
)

settings = get_settings(os.getenv("CONFIG_FILE"))

router = APIRouter(prefix="/api/bulk", tags=[APITags.bulk])


@router.get("/list-tickers", response_model=dict[str, list[ExchangeTickerInfo] | None])
async def list_exchange_wise_ticker() -> ORJSONResponse:
    """Get all the available `ticker` for all `exchange`"""
    all_exchanges = {}

    for exch in StockExchange:
        table_path = settings.stockdb.data_base_path / f"{exch.value}/equity"
        if not table_path.exists():
            all_exchanges[exch.value] = None
        else:
            result = await (
                pl.scan_delta(table_path)
                .select(pl.col("symbol").alias("ticker"), "company")
                .sort("ticker")
                .collect_async()
            )
            all_exchanges[exch.value] = result.to_dicts()

    return ORJSONResponse(all_exchanges)


@router.get("/list-indexes", response_model=dict[str, list[str] | None])
async def list_exchange_wise_indexes() -> ORJSONResponse:
    """Get all the available `index_symbol` for all `exchange`"""
    exch = Exchange()
    all_exchanges = {}

    for exch_name in StockExchange:
        try:
            exch_accessor = getattr(exch, exch_name.value.lower())
            all_exchanges[exch_name.value] = exch_accessor.get_index_list()
        # NOTE - Some exchanges may not have index info implemented. So there won't be any accessor
        # property for those exchanges in `Exchange` class.
        except AttributeError:
            all_exchanges[exch_name.value] = None

    return ORJSONResponse(all_exchanges)
