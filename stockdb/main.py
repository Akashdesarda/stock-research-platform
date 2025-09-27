import http
import logging
import traceback

from about_time import about_time
from api.config import Settings
from api.models import APITags
from api.routers import per_security
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference

logger = logging.getLogger("stockdb")
settings = Settings()

app = FastAPI(
    debug=True, title="StockDB API", version="0.0.3", docs_url=None, redoc_url=None
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


# REST API for health check
@app.get("/", status_code=200, tags=[APITags.root])
async def _index():
    """API Health check"""
    return {"message": "StockDB API is up and running"}


# adding all the routers from submodules wrt to v2 model
app.include_router(per_security.router, tags=[APITags.per_security])


# Scalar interactive docs
@app.get("/docs", include_in_schema=False)
async def _internal_scalar_html():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)
