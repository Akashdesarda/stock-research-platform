import os

import polars as pl
import streamlit as st
from stocksense.config import get_settings

from app.core.utils import (
    get_available_exchanges,
    get_available_tickers,
    rest_request_sync,
)

settings = get_settings(os.getenv("CONFIG_FILE"))

available_exchange = get_available_exchanges()
available_tickers = get_available_tickers()

st.markdown("Manage application settings and configurations.")

# using tab layout for different management sections
tasks_tab, config_tab = st.tabs(["🔧Tasks", "⚙️ Configuration"])
with tasks_tab:
    # SECTION - Data update task
    st.markdown("### Update ticker history data")
    task_mode_radio, download_mode_radio, exchange_dropdown = st.columns([
        0.3,
        0.3,
        0.4,
    ])

    with task_mode_radio:
        task_mode = st.radio(
            "Task Mode",
            options=["auto", "manual"],
            index=0,
            horizontal=True,
            help="`auto` mode will determine all required tickers & their update needs, `manual` allows user to select tickers, start date and end date manually.",
        )
        # updating state
        st.session_state.task_mode_mngt = task_mode

    with download_mode_radio:
        download_mode = st.radio(
            "Download Mode",
            options=["incremental", "full"],
            index=0,
            horizontal=True,
            help="`full` mode will redownload all data, `incremental` will only fetch new data since last update.",
        )
        # updating state
        st.session_state.download_mode_mngt = download_mode

    with exchange_dropdown:
        selected_exchange = st.selectbox(
            "Select Exchange",
            options=available_exchange.select("dropdown").to_series().to_list(),
            index=0,
            help="Select the exchange for which ticker data needs to be updated.",
        )
        # updating state
        st.session_state.selected_exchange_mngt = (
            available_exchange.filter(pl.col("dropdown") == selected_exchange)
            .select("symbol")
            .item()
        )

    # ticker history update form
    with st.form("data_update_form", border=True):
        if st.session_state.task_mode_mngt == "manual":
            st.write("Manual Mode Selected - Please select tickers and date range.")

            # ticker selection multiselect
            selected_tickers = st.multiselect(
                "Select Tickers",
                options=available_tickers[st.session_state.selected_exchange_mngt]
                # .filter(pl.col("dropdown") == selected_exchange)
                .select("ticker")
                .to_series()
                .to_list(),
                help="Select one or more tickers to update data for.",
            )
            # updating state
            st.session_state.selected_tickers_mngt = selected_tickers

            # date range selection
            date_selection = st.date_input(
                "Custom Date Range",
                value=[],
                # help="If set, 'Data Period' selection is ignored.",
                max_value="today",
            )
            # updating state
            st.session_state.date_selection_mngt = date_selection

        elif st.session_state.task_mode_mngt == "auto":
            st.session_state.selected_tickers_mngt = None
            st.session_state.date_selection_mngt = None
            st.session_state.end_date_mngt = None
            st.info(
                "Auto Mode Selected - Tickers and date range will be determined automatically."
            )

        # submit button
        if submit := st.form_submit_button("Submit", icon=":material/play_arrow:"):
            with st.spinner("Executing data update task..."):
                # Call the API to trigger data update task
                payload = {
                    "task_mode": st.session_state.task_mode_mngt,
                    "download_mode": st.session_state.download_mode_mngt,
                    "exchange": st.session_state.selected_exchange_mngt,
                    "ticker": st.session_state.selected_tickers_mngt,
                    "start_date": st.session_state.date_selection_mngt[0]
                    if st.session_state.task_mode_mngt == "manual"
                    else None,
                    "end_date": st.session_state.date_selection_mngt[1]
                    if st.session_state.task_mode_mngt == "manual"
                    else None,
                }
                response = rest_request_sync(
                    url=f"{settings.common.base_url}:{settings.stockdb.port}/api/task/ticker/history",
                    method="POST",
                    payload_data=payload,
                )
            if response.status_code == 200:
                st.success("Data update task successfully completed!")
            else:
                st.error(response.json()["detail"])
