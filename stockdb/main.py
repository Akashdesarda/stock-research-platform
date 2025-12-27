import http
import logging
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path as Pathlib_Path

import polars as pl
from about_time import about_time
from api import setup
from api.models import APITags, StockExchange
from api.routers import bulk, per_security, tasks
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from scalar_fastapi import get_scalar_api_reference
from stocksense.config import get_settings
from stocksense.data import StockDataDB

logger = logging.getLogger("stockdb")
settings = get_settings(os.getenv("CONFIG_FILE"))
STATIC_DIR = Pathlib_Path(__file__).parent / "static"  # points to stockdb/static

app = FastAPI(
    debug=True, title="StockDB API", version="1.1.4", docs_url=None, redoc_url=None
)


# Middleware to log incoming request & processing timing
@app.middleware("http")
async def _log_request_information(request: Request, call_next):
    # Reconstruct the path and query string without sensitive data
    path_and_query_url = (
        f"{request.url.path}?{request.query_params}"
        if request.query_params
        else request.url.path
    )

    # tracking time taken by request to be fulfilled
    with about_time() as t:  # type: ignore
        # NOTE - Here the actual http function will be executed in the middleware.
        logger.info(f"received request --> {request.method} {path_and_query_url}")
        response = await call_next(request)
        logger.info(
            f"fulfilled request --> {request.method} {path_and_query_url} {response.status_code}"
            f" {http.HTTPStatus(response.status_code).phrase} in {t.duration_human}"
        )
        return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # to log error message to azure app insights
    errors = traceback.format_exception(exc)
    logger.error("".join(errors))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": exc.__class__.__name__, "detail": str(exc)},
    )


# Serve static assets and favicon
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# REST API for health check
@app.get("/", status_code=200, tags=[APITags.root])
async def _index():
    """API Health check"""
    return {"message": "StockDB API is up and running"}


@app.get("/health/api", status_code=200, tags=[APITags.health])
async def _health():
    """API Health check"""
    return {"message": "StockDB API is up and running"}


@app.get(
    "/health/data/",
    status_code=200,
    tags=[APITags.health],
    response_class=ORJSONResponse,
)
async def _stockdb_data_health() -> dict:
    # REVIEW - Should I add more exchange info?
    """StockDB Data Health check"""
    all_exchanges = dict.fromkeys(StockExchange.__members__.keys())
    now = datetime.now()
    latest_data_date = now.date() if now.hour >= 18 else now.date() - timedelta(days=1)

    # Getting data health loop
    for exch in all_exchanges:
        stock_db = StockDataDB(
            settings.stockdb.data_base_path / f"{exch}/ticker_history"
        )
        count = await stock_db.table_data.select("close").count().collect_async()
        if count.item() == 0:
            all_exchanges[exch] = "NO DATA"
            continue
        date_check = (
            await stock_db.polars_filter(
                pl.col("date").max().cast(pl.Date) < latest_data_date
            )
            .select("close")
            .count()
            .collect_async()
        )

        all_exchanges[exch] = "OK" if date_check.item() == 0 else "OUTDATED"

    return all_exchanges


# adding all the routers from submodules
app.include_router(per_security.router)
app.include_router(tasks.router)
app.include_router(bulk.router)


# Scalar interactive docs
@app.get("/docs", include_in_schema=False)
async def _internal_scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
        scalar_favicon_url="/static/chart-growth-invest.svg",
    )


if __name__ == "__main__":
    import uvicorn

    # FIXME - remove below prints after testing
    print("initial", os.getenv("CONFIG_FILE"))
    setup()
    print("after setup", os.getenv("CONFIG_FILE"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.stockdb.port,
        access_log=False,
    )
