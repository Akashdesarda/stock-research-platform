import os

import httpx
import polars as pl
import streamlit as st
from stocksense.config import get_settings

from app.state.model import PreviewMethodChoice

settings = get_settings(os.getenv("CONFIG_FILE"))


def fetch_data_from_sql_query(exchange: str, sql_query: str) -> pl.LazyFrame | None:
    response = httpx.post(
        url=f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security/{exchange}/query",
        json={"sql_query": sql_query},
    )
    if response.status_code == 200:
        st.success("Data fetched successfully!")
        return pl.LazyFrame(response.json())
    else:
        st.error(f"Error fetching data: {response.json()['detail']}")
        # Return empty DataFrame on error
        # return pl.LazyFrame([])


def fetch_data_from_form(
    exchange: str, params: dict, selected_tickers: pl.DataFrame
) -> list[pl.LazyFrame]:
    data_collection = []
    with httpx.Client(
        base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security/{exchange}",
        params=params,
    ) as client:
        for ticker in selected_tickers.iter_rows():
            response = client.get(f"/{ticker[0]}/history")
            if response.status_code == 200:
                data_collection.append(pl.LazyFrame(response.json()))
            else:
                st.error(f"Error fetching data for {ticker[0]}")
        st.success("Data fetched successfully!")
    return data_collection


def data_preview(
    data: pl.LazyFrame | list[pl.LazyFrame],
    preview_method: PreviewMethodChoice,
    n_rows: int,
    start_idx: int,
    end_idx: int,
) -> pl.LazyFrame:
    query_data = pl.concat(data) if isinstance(data, list) else data

    # return data based on selected method
    match preview_method:
        case PreviewMethodChoice.head:
            return query_data.head(n_rows)
        case PreviewMethodChoice.tail:
            return query_data.tail(n_rows)
        case PreviewMethodChoice.desired:
            return query_data.slice(start_idx, end_idx - start_idx)
        case PreviewMethodChoice.random:
            return (
                query_data.with_row_index()
                .with_columns(pl.col("index").shuffle(seed=42).alias("_rand"))
                .sort("_rand")
                .limit(n_rows)
                .drop("index", "_rand")
                .sort("date")
            )
        case _:
            raise ValueError(f"preview method must be from {list(PreviewMethodChoice)}")
