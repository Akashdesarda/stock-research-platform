import polars as pl
from duckdb import BinderException, ParserException
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import ORJSONResponse
from stocksense.config import get_settings
from stocksense.data import Exchange, StockDataDB

from api.models import (
    APITags,
    ExchangeTickerInfo,
    StockExchange,
    TickerHistoryOutput,
    TickerQueryInput,
)

settings = get_settings()

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
                pl
                .scan_delta(table_path)
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


@router.post("/query", response_model=TickerHistoryOutput)
async def ticker_query(input_body: TickerQueryInput) -> ORJSONResponse:
    """Get stock history data for given `exchange` using SQL query"""
    history_data = StockDataDB(
        settings.stockdb.data_base_path / f"{input_body.exchange.value}/ticker_history"
    )
    # Execute SQL query
    try:
        result = history_data.sql_filter(input_body.sql_query).with_columns(
            pl.col(pl.Decimal).cast(pl.Float64)
        )
        result = await result.collect_async()
        return ORJSONResponse(result.to_dicts())
    except (BinderException, ParserException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
