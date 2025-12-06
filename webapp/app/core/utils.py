import httpx
import orjson
import polars as pl
import streamlit as st

from app.config import Settings

settings = Settings()


def rest_request_sync(
    url: str,
    method: str = "GET",
    payload_data: dict | None = None,
    query_params: dict | None = None,
    headers: dict | None = None,
    timeout: int | httpx.Timeout | None = httpx.Timeout(
        read=None, write=None, connect=3, pool=10
    ),
    **kwargs,
) -> httpx.Response:
    timeout = httpx.Timeout(timeout)
    params = httpx.QueryParams(query_params) if query_params else None

    with httpx.Client(timeout=timeout, **kwargs) as client:
        response = client.request(
            method=method,
            url=url,
            params=params,
            content=orjson.dumps(payload_data) if payload_data else None,
            headers=headers,
        )

    return response


@st.cache_data(show_spinner=True)
def get_available_exchanges() -> pl.DataFrame:
    exch_response = rest_request_sync(
        url=f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security",
        method="GET",
        follow_redirects=True,
    ).json()
    return pl.DataFrame({
        "symbol": exch_response.keys(),
        "name": exch_response.values(),
    }).with_columns(dropdown=pl.col("name") + " (" + pl.col("symbol") + ")")


@st.cache_data(show_spinner=True)
def get_available_tickers(available_exchange: list[str]) -> dict[str, pl.DataFrame]:
    available_tickers = dict.fromkeys(available_exchange, pl.DataFrame())
    for exch in available_tickers:
        _ = rest_request_sync(
            url=f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security/{exch}",
            method="GET",
            follow_redirects=True,
        )
        if _.status_code == 200:
            available_tickers[exch] = pl.DataFrame(_.json())
            available_tickers[exch] = available_tickers[exch].with_columns(
                dropdown=pl.col("ticker") + " - " + pl.col("company")
            )
        else:
            available_tickers[exch] = pl.DataFrame({
                "ticker": [],
                "company": [],
            }).with_columns(dropdown=pl.lit(""))
    return available_tickers
