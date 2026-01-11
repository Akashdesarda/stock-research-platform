import httpx
import polars as pl
import streamlit as st
from stocksense.config import get_settings

from app.state.model import PreviewMethodChoice

settings = get_settings()


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


def data_preview_control(
    key_suffix: str,
    current_n_rows: int,
    current_start: int,
    current_end: int,
):
    # nothing is shown until the user picks a real method)
    preview_n_rows, start_idx, end_idx = current_n_rows, current_start, current_end
    preview_col, control_col = st.columns([0.3, 0.7])
    with preview_col:
        preview_method_choice = st.radio(
            "Preview Method",
            options=list(PreviewMethodChoice),
            format_func=lambda x: x.value,
            index=None,
            key=f"preview_method_choice_{key_suffix}",
            help="Choose how to preview the data",
        )

    # Control widgets use keys so their values persist even when
    # the radio changes (avoids losing slider/number inputs)
    with control_col:
        if preview_method_choice in [
            PreviewMethodChoice.head,
            PreviewMethodChoice.tail,
            PreviewMethodChoice.random,
        ]:
            preview_n_rows = st.slider(
                "Number of rows",
                min_value=1,
                max_value=100,
                value=current_n_rows,
                key=f"preview_n_rows_{key_suffix}",
                help="Number of rows to display",
            )
        elif preview_method_choice is PreviewMethodChoice.desired:
            range_col1, range_col2 = st.columns(2)
            with range_col1:
                start_idx = st.number_input(
                    "Start index",
                    min_value=0,
                    value=current_start,
                    step=1,
                    key=f"preview_start_idx_{key_suffix}",
                    help="Starting row index (0-based)",
                )
            with range_col2:
                end_idx = st.number_input(
                    "End index",
                    min_value=1,
                    value=current_end,
                    step=1,
                    key=f"preview_end_idx_{key_suffix}",
                    help="Ending row index (exclusive)",
                )

    return preview_method_choice, preview_n_rows, start_idx, end_idx


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
                query_data
                .with_row_index()
                .with_columns(pl.col("index").shuffle(seed=42).alias("_rand"))
                .sort("_rand")
                .limit(n_rows)
                .drop("index", "_rand")
                .sort("date")
            )
        case _:
            raise ValueError(f"preview method must be from {list(PreviewMethodChoice)}")
