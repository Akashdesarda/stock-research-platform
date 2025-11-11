import httpx
import polars as pl
import streamlit as st

from app.config import Settings

settings = Settings()


st.title("Data Explore")
st.markdown("Explore stock data and analytics.")

# SECTION - Preparing query to pull data
with httpx.Client(
    base_url=f"{settings.common.base_url}:{settings.stockdb.port}",
    follow_redirects=True,
) as client:
    # exchange dropdown data
    exch_response = client.get("/api/per-security").json()
    available_exchange = pl.DataFrame({
        "symbol": exch_response.keys(),
        "name": exch_response.values(),
    }).with_columns(dropdown=pl.col("name") + " (" + pl.col("symbol") + ")")
    # ticker dropdown data
    available_tickers = dict.fromkeys(
        available_exchange.select("symbol").to_series().to_list()
    )
    for exch in available_tickers:
        _ = client.get(f"/api/per-security/{exch}")
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


# create tabs for manual and AI-powered queries
manual_query, ai_query = st.tabs([
    "📝 Manual Data Query",
    "✨ AI-Powered Data Query",
])

# SECTION - Manual Data Query tab
with manual_query:
    st.subheader("Manual Data Query")
    # SECTION - Exchange and Ticker Selection
    st.write("Exchange and Ticker Selection")

    exchange_col, ticker_col = st.columns(2)
    # exchange selection dropdown
    with exchange_col:
        selected_exchange = st.selectbox(
            "Select Exchange",
            options=available_exchange.select("dropdown").to_series().to_list(),
        )
        # updating state
        st.session_state.selected_exchange = (
            available_exchange.filter(pl.col("dropdown") == selected_exchange)
            .select("symbol")
            .item()
        )
    # ticker selection dropdown
    with ticker_col:
        tickers_selection_choice = st.selectbox(
            "Choice how to select tickers",
            options=[
                "Desired",
                "Index Based",
                "All",
            ],
        )
        # updating state
        st.session_state.tickers_selection_choice = tickers_selection_choice

    # SECTION - Query Form
    with st.form(key="manual_data_query_form", border=True):
        # ticker symbol selection
        if st.session_state.tickers_selection_choice == "All":
            st.multiselect("Ticker Symbols", disabled=True, options=[])
            selected_tickers = available_tickers[
                st.session_state.selected_exchange
            ].select("ticker")
        elif st.session_state.tickers_selection_choice == "Index Based":
            st.error("Index Based selection is not yet implemented.")
            selected_tickers = pl.DataFrame([])
        elif st.session_state.tickers_selection_choice == "Desired":
            _ = st.multiselect(
                "Ticker Symbols",
                options=available_tickers[st.session_state.selected_exchange][
                    "dropdown"
                ].to_list(),
            )
            selected_tickers = (
                available_tickers[st.session_state.selected_exchange]
                .filter(pl.col("dropdown").is_in(_))
                .select("ticker")
            )

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

        if user_query := st.text_area("Use your own query:"):
            st.code(user_query, language="sql")
        submit_query = st.form_submit_button("Submit", icon=":material/play_arrow:")

with ai_query:
    st.subheader("AI-Powered Data Query")
    # Add AI query components here

if submit_query:
    # SECTION - Getting the data based on query
    query_data_collection = []
    with httpx.Client(
        base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security/{st.session_state.selected_exchange}",
        params={
            "interval": selected_interval,
            "period": selected_period,
            # "start": date_selection[0].strftime("%Y-%m-%d") if len(date_selection) == 2 else None,
            # "end": date_selection[1].strftime("%Y-%m-%d") if len(date_selection) == 2 else None,
        },
    ) as client:
        for ticker in selected_tickers.iter_rows():
            response = client.get(f"/{ticker[0]}/history")
            if response.status_code == 200:
                query_data_collection.append(pl.LazyFrame(response.json()))
            else:
                st.error(f"Error fetching data for {ticker[0]}")

    # Store the results in session state
    st.session_state.query_data_collection = query_data_collection
    st.session_state.query_submitted = True


# SECTION - Query data Preview
with st.container():
    if st.session_state.get("query_submitted", False):
        st.subheader("Query Data Preview")
        query_data = pl.concat(st.session_state.query_data_collection)

        # Preview options
        preview_col, control_col = st.columns([0.3, 0.7])

        with preview_col:
            preview_method = st.radio(
                "Preview Method",
                options=["Head", "Tail", "Desired Range", "Random"],
                index=None,
                help="Choose how to preview the data",
            )

        # Initialize variables
        n_rows = 10
        start_idx = 0
        end_idx = 10

        with control_col:
            if preview_method in ["Head", "Tail", "Random"]:
                n_rows = st.slider(
                    "Number of rows",
                    min_value=1,
                    max_value=100,
                    value=10,
                    help="Number of rows to display",
                )
            elif preview_method == "Desired Range":
                range_col1, range_col2 = st.columns(2)
                with range_col1:
                    start_idx = st.number_input(
                        "Start index",
                        min_value=0,
                        value=0,
                        step=1,
                        help="Starting row index (0-based)",
                    )
                with range_col2:
                    end_idx = st.number_input(
                        "End index",
                        min_value=1,
                        value=10,
                        step=1,
                        help="Ending row index (exclusive)",
                    )

        # Display data based on selected method
        if preview_method == "Head":
            st.dataframe(query_data.head(n_rows).collect())
        elif preview_method == "Tail":
            st.dataframe(query_data.tail(n_rows).collect())
        elif preview_method == "Desired Range":
            st.dataframe(query_data.slice(start_idx, end_idx - start_idx).collect())
        elif preview_method == "Random":
            st.dataframe(
                query_data.with_row_index()
                .with_columns(pl.col("index").shuffle(seed=42).alias("_rand"))
                .sort("_rand")
                .limit(n_rows)
                .drop("index", "_rand")
                .sort("date")
                .collect()
            )
