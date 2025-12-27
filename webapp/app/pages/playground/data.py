import os

import polars as pl
import streamlit as st
from stocksense.ai.agents import StockDBContextDependency, text_to_sql
from stocksense.config import get_settings

from app.core.utils import (
    get_available_exchanges,
    get_available_tickers,
    get_ticker_history_columns,
)
from app.pages.playground._helper import (
    data_preview,
    fetch_data_from_form,
    fetch_data_from_sql_query,
)
from app.state.manager import StateManager
from app.state.model import PreviewMethodChoice, TickerChoice

settings = get_settings(os.getenv("CONFIG_FILE"))
state = StateManager.init()

st.markdown("# Data Explorer")
st.markdown("Explore stock data and analytics.")

available_exchange = get_available_exchanges()
available_tickers = get_available_tickers(
    available_exchange.select("symbol").to_series().to_list()
)

# create tabs for manual and AI-powered queries
manual_query, ai_query = st.tabs([
    "📝 Manual Data Query",
    "✨ AI-Powered Data Query",
])

# NOTE - Throughout the page DO NOT assign widgets values directly to state manager, because
# Streamlit runs entire page & initial value `None` is rendered. Instead use explicitly guard `None`
# by 2-step value assignment

# SECTION - Manual Data Query tab
with manual_query:
    st.subheader("Manual Data Query")
    # SECTION - Exchange and Ticker Selection
    st.write("Exchange and Ticker Selection")

    exchange_col, ticker_col = st.columns(2)
    # exchange selection dropdown
    # NOTE - storing selected exchange, tickers in session state for inter-widgets & cross-tab access
    with exchange_col:
        selected_exchange = st.selectbox(
            "Select Exchange",
            options=available_exchange.select("dropdown").to_series().to_list(),
            key="exchange_selection_manual",
        )
        # updating state
        state.selected_exchange_data = (
            available_exchange.filter(pl.col("dropdown") == selected_exchange)
            .select("symbol")
            .item()
        )
    # ticker selection dropdown
    with ticker_col:
        tickers_selection_choice = st.selectbox(
            "Choice how to select tickers",
            options=list(TickerChoice),
            format_func=lambda x: x.value,
            key="ticker_selection_manual",
        )
        # updating state
        state.ticker_choice_data = tickers_selection_choice

    # SECTION - Query Form
    with st.form(key="manual_data_query_form", border=True):
        # ticker symbol selection
        match state.ticker_choice_data:
            case TickerChoice.all:
                st.multiselect("Ticker Symbols", disabled=True, options=[])
                selected_tickers = available_tickers[
                    state.selected_exchange_data
                ].select("ticker")
            case TickerChoice.index:
                st.error("Index Based selection is not yet implemented.")
                selected_tickers = pl.DataFrame([])
            case TickerChoice.desired:
                _ = st.multiselect(
                    "Ticker Symbols",
                    options=available_tickers[state.selected_exchange_data][
                        "dropdown"
                    ].to_list(),
                )
                selected_tickers = (
                    available_tickers[state.selected_exchange_data]
                    .filter(pl.col("dropdown").is_in(_))
                    .select("ticker")
                )
            case _:
                selected_tickers = pl.DataFrame([])

        # SECTION - Time Range Selection
        st.write("Time Range Selection")
        interval_col, space_col, period_col, separator_col, date_col = st.columns([
            0.20,
            0.15,
            0.20,
            0.1,
            0.35,
        ])
        # interval selection dropdown
        with interval_col:
            selected_interval = st.selectbox(
                "Data Interval",
                options=[
                    "1d",
                    "3d",
                    "5d",
                    "1wk",
                    "3wk",
                    "5wk",
                    "1mo",
                    "3mo",
                    "5mo",
                ],
                index=0,
                help="Time interval between historical data points",
            )
        # horizontal spacer
        with space_col:
            st.space("medium")
        # period selection dropdown
        with period_col:
            selected_period = st.selectbox(
                "Data Period",
                options=[
                    "1mo",
                    "3mo",
                    "6mo",
                    "1y",
                    "2y",
                    "5y",
                    "10y",
                    "ytd",
                    "max",
                ],
                index=2,
                help="Day period between historical data points",
            )
        # Vertical separator
        with separator_col:
            st.markdown(
                """
                <div style='height: 30px; display: flex; align-items: flex-end; justify-content: center;'>
                    <span style='color: #666; font-weight: bold; font-size: 14px;'>OR</span>
                </div>
                <div style='height: 50px; display: flex; align-items: center; justify-content: center;'>
                    <div style='border-left: 2px solid #ccc; height: 40px;'></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        # date range selection
        with date_col:
            date_selection = st.date_input(
                "Custom Date Range",
                value=[],
                help="If set, 'Data Period' selection is ignored.",
                max_value="today",
            )
        # custom query input
        if user_query := st.text_area(
            "Use your own sql query",
        ):
            # storing in state so that it can be accessed outside of form
            state.user_query_data = user_query

        # preview data option
        preview_selection_data = st.checkbox("Preview Data", value=True)
        state.preview_selection_data = preview_selection_data

        # submit query button
        manual_submit_query = st.form_submit_button(
            "Submit", icon=":material/play_arrow:"
        )

    # SECTION - Data preview for manual query
    if manual_submit_query:
        st.subheader("Query Data Preview")
        if user_query:
            # Fetch data based on sql query
            query_manual_collection_data = fetch_data_from_sql_query(
                state.selected_exchange_data, user_query
            )
        else:
            # Fetch data based on form inputs
            query_manual_collection_data = fetch_data_from_form(
                exchange=state.selected_exchange_data,
                params={
                    "interval": selected_interval,
                    "period": selected_period,
                },
                selected_tickers=selected_tickers,
            )
        state.query_manual_collection_data = query_manual_collection_data

    # Persisted preview rendering (survives widget interactions)
    if (state.preview_selection_data is True) and (
        state.query_manual_collection_data is not None
    ):
        with st.container():
            st.subheader("Query Data Preview")
            # If used custom query the displaying in proper format
            if state.user_query_data:
                st.write("Executed SQL Query:")
                st.code(
                    state.user_query_data,
                    language="sql",
                    line_numbers=True,
                    wrap_lines=True,
                )

            # Preview options (explicit "Select Preview" as first choice so
            # nothing is shown until the user picks a real method)
            preview_col, control_col = st.columns([0.3, 0.7])
            with preview_col:
                preview_method_choice_data = st.radio(
                    "Preview Method",
                    options=list(PreviewMethodChoice),
                    format_func=lambda x: x.value,
                    index=None,
                    key="preview_method_choice_manual",
                    help="Choose how to preview the data",
                )
                state.preview_method_choice_data = preview_method_choice_data

            # Control widgets use keys so their values persist even when
            # the radio changes (avoids losing slider/number inputs)
            with control_col:
                if state.preview_method_choice_data in [
                    PreviewMethodChoice.head,
                    PreviewMethodChoice.tail,
                    PreviewMethodChoice.random,
                ]:
                    n_rows = st.slider(
                        "Number of rows",
                        min_value=1,
                        max_value=100,
                        value=state.preview_n_rows_data,
                        key="preview_n_rows_manual",
                        help="Number of rows to display",
                    )
                    state.preview_n_rows_data = n_rows
                elif state.preview_method_choice_data is PreviewMethodChoice.desired:
                    range_col1, range_col2 = st.columns(2)
                    with range_col1:
                        start_idx = st.number_input(
                            "Start index",
                            min_value=0,
                            value=state.preview_start_idx_data,
                            step=1,
                            key="preview_start_idx_manual",
                            help="Starting row index (0-based)",
                        )
                        state.preview_start_idx_data = start_idx
                    with range_col2:
                        end_idx = st.number_input(
                            "End index",
                            min_value=1,
                            value=state.preview_end_idx_data,
                            step=1,
                            key="preview_end_idx_manual",
                            help="Ending row index (exclusive)",
                        )
                        state.preview_end_idx_data = end_idx

            # Only preview when a real method is selected
            if state.preview_method_choice_data:
                preview_data = data_preview(
                    data=state.query_manual_collection_data,
                    preview_method=state.preview_method_choice_data,
                    n_rows=int(state.preview_n_rows_data),
                    start_idx=int(state.preview_start_idx_data),
                    end_idx=int(state.preview_end_idx_data),
                )
                st.dataframe(preview_data)
            else:
                st.info("Select a preview method to display data.")


with ai_query:
    st.subheader("AI-Powered Data Query")
    # exchange_col, query_prompt_col = st.columns([0.3, 0.7])

    # exchange selection dropdown
    # NOTE - storing selected exchange, prompt in session state for inter-widgets & cross-tab access
    selected_exchange = st.selectbox(
        "Select Exchange",
        options=available_exchange.select("dropdown").to_series().to_list(),
        key="select_exchange_manual",
    )
    # updating state
    state.selected_exchange_data = (
        available_exchange.filter(pl.col("dropdown") == selected_exchange)
        .select("symbol")
        .item()
    )

    if query_prompt := st.chat_input("Enter your data query prompt"):
        state.query_prompt = query_prompt

    if state.query_prompt and state.agent_text_to_sql is None:
        stockdb_ctx = StockDBContextDependency(columns=get_ticker_history_columns())
        with st.status("Generating SQL query...") as status:
            agent = text_to_sql(
                model_name=settings.app.text_to_sql_model,
                api_key=getattr(
                    settings.common,
                    f"{settings.app.text_to_sql_model.split(':')[0].split('-')[0].upper()}_API_KEY",
                ),
            )
            st.write(f"Text-to-SQL agent working with {settings.app.text_to_sql_model}")
            state.agent_text_to_sql = agent.run_sync(
                state.query_prompt, deps=stockdb_ctx
            )
            st.write("Text-to-SQL agent generated query successfully!")

    if state.agent_text_to_sql:
        with st.form("ai_data_query_form", border=True):
            user_query = state.agent_text_to_sql.output.sql_query
            st.code(user_query, language="sql")
            # preview data option
            preview_selection_data = st.checkbox("Preview Data", value=True)
            state.preview_selection_data = preview_selection_data
            # submit query button
            ai_submit_query = st.form_submit_button(
                "Submit", icon=":material/play_arrow:"
            )

        # SECTION - AI Query Data Preview
        if ai_submit_query:
            # Fetch data based on sql query & storing into sate
            state.query_ai_collection_data = fetch_data_from_sql_query(
                exchange=state.selected_exchange_data,
                sql_query=user_query,
            )

        # Persisted preview rendering (survives widget interactions)
        if (state.preview_selection_data is True) and (
            state.query_ai_collection_data is not None
        ):
            with st.container():
                st.subheader("Query Data Preview")

                # nothing is shown until the user picks a real method)
                preview_col, control_col = st.columns([0.3, 0.7])
                with preview_col:
                    preview_method_choice_ai = st.radio(
                        "Preview Method",
                        options=list(PreviewMethodChoice),
                        format_func=lambda x: x.value,
                        index=None,
                        key="preview_method_choice_ai",
                        help="Choose how to preview the data",
                    )
                    state.preview_method_choice_data = preview_method_choice_ai

                # Control widgets use keys so their values persist even when
                # the radio changes (avoids losing slider/number inputs)
                with control_col:
                    if state.preview_method_choice_data in [
                        PreviewMethodChoice.head,
                        PreviewMethodChoice.tail,
                        PreviewMethodChoice.random,
                    ]:
                        preview_n_rows_ai = st.slider(
                            "Number of rows",
                            min_value=1,
                            max_value=100,
                            value=state.preview_n_rows_data,
                            key="preview_n_rows_ai",
                            help="Number of rows to display",
                        )
                        state.preview_n_rows_data = preview_n_rows_ai
                    elif (
                        state.preview_method_choice_data is PreviewMethodChoice.desired
                    ):
                        range_col1, range_col2 = st.columns(2)
                        with range_col1:
                            start_idx_ai = st.number_input(
                                "Start index",
                                min_value=0,
                                value=state.preview_start_idx_data,
                                step=1,
                                key="preview_start_idx_ai",
                                help="Starting row index (0-based)",
                            )
                            state.preview_start_idx_data = start_idx_ai
                        with range_col2:
                            end_idx_ai = st.number_input(
                                "End index",
                                min_value=1,
                                value=state.preview_end_idx_data,
                                step=1,
                                key="preview_end_idx_ai",
                                help="Ending row index (exclusive)",
                            )
                            state.preview_end_idx_data = end_idx_ai

                # Only preview when a real method is selected
                if state.preview_method_choice_data:
                    preview_data = data_preview(
                        data=state.query_ai_collection_data,
                        preview_method=state.preview_method_choice_data,
                        n_rows=int(state.preview_n_rows_data),
                        start_idx=int(state.preview_start_idx_data),
                        end_idx=int(state.preview_end_idx_data),
                    )
                    st.dataframe(preview_data)
                else:
                    st.info("Select a preview method to display data.")
