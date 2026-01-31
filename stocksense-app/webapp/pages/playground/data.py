import reflex as rx
import reflex_enterprise as rxe
from stocksense.types import DataInterval, DataPeriod

from webapp.components.inputs import (
    cancel_button,
    checkbox_input,
    date_range_picker,
    dropdown_select,
    multi_select_dropdown,
    submit_button,
    text_area,
)
from webapp.components.layout import (
    bordered_container,
    form_field,
    page_layout,
    section_header,
)
from webapp.state.playground import DataState
from webapp.types import TickerChoice


def _index_based_ticker_selection() -> rx.Component:
    return dropdown_select(
        label="Select Index",
        options=DataState.available_index,
        value=DataState.index_choice,
        on_change=DataState.set_index_choice,
        disabled=DataState.ticker_choice != TickerChoice.index.value,
        width="100%",
    )


def _desired_ticker_selection() -> rx.Component:
    return multi_select_dropdown(
        label="Ticker Symbols",
        options=DataState.ticker_dropdown_list,
        value=DataState.selected_ticker_dropdowns,
        on_change=DataState.get_tickers_for_desired,
        placeholder="Choose options",
        disabled=DataState.ticker_choice != TickerChoice.desired.value,
        width="100%",
    )


def _all_ticker_selection() -> rx.Component:
    # NOTE - # No selection needed for "All" option
    return rx.callout(
        "All tickers from the selected exchange will be included.",
        color_scheme="blue",
        icon="info",
        width="100%",
    )


def _results_view() -> rx.Component:
    """Shared view for displaying fetched data results."""
    return rx.cond(
        DataState.preview_enabled & DataState.fetch_data_ready,
        rx.vstack(
            rx.separator(size="4", width="100%"),
            rx.text("Data Preview", size="4", weight="medium"),
            rxe.ag_grid(
                id="data_preview_grid",
                row_data=DataState.data,
                column_defs=DataState.columns_def,
                pagination=True,
                pagination_page_size=10,
                pagination_page_size_selector=[10, 40, 100],
                width="100%",
                height="500px",
            ),
            width="100%",
            spacing="4",
        ),
        rx.fragment(),
    )


def data() -> rx.Component:
    """Playground → Data page.

    Placeholder while the Streamlit → Reflex migration is in progress.
    """

    manual_tab = rx.tabs.content(
        rx.vstack(
            rx.text("Manual Data Query", size="4", weight="medium"),
            bordered_container(
                rx.vstack(
                    # SECTION - Exchange and Ticker
                    rx.vstack(
                        rx.text(
                            "Exchange and Ticker Selection",
                            size="2",
                            weight="medium",
                            color_scheme="gray",
                        ),
                        rx.hstack(
                            form_field(
                                label="Select Exchange",
                                control=dropdown_select(
                                    label="Select Exchange",
                                    options=DataState.exchange_dropdown_list,
                                    value=DataState.selected_exchange_dropdown,
                                    on_change=DataState.set_exchange_dropdown,
                                    placeholder="Choose an exchange",
                                    width="100%",
                                ),
                            ),
                            form_field(
                                label="Ticker Selection Mode",
                                control=dropdown_select(
                                    label="Ticker Selection Mode",
                                    options=[i.value for i in TickerChoice],
                                    value=DataState.ticker_choice,
                                    on_change=DataState.set_ticker_choice,
                                    placeholder="Choose a mode",
                                    width="100%",
                                ),
                            ),
                            width="100%",
                            spacing="4",
                        ),
                        rx.match(
                            DataState.ticker_choice,
                            (TickerChoice.index.value, _index_based_ticker_selection()),
                            (TickerChoice.desired.value, _desired_ticker_selection()),
                            (TickerChoice.all.value, _all_ticker_selection()),
                        ),
                        width="100%",
                        spacing="4",
                    ),
                    rx.separator(size="4", width="100%"),
                    # SECTION - Time Range
                    rx.vstack(
                        rx.text(
                            "Time Range Selection",
                            size="2",
                            weight="medium",
                            color_scheme="gray",
                        ),
                        rx.hstack(
                            form_field(
                                label="Data Interval",
                                control=dropdown_select(
                                    label="Data Interval",
                                    options=[i.value for i in DataInterval],
                                    value=DataState.interval,
                                    on_change=DataState.set_interval,
                                    width="100%",
                                ),
                                help_text="Time interval between historical data points",
                            ),
                            rx.spacer(),
                            width="100%",
                            spacing="4",
                        ),
                        rx.hstack(
                            form_field(
                                label="Data Period",
                                control=dropdown_select(
                                    label="Data Period",
                                    options=[i.value for i in DataPeriod],
                                    value=DataState.period,
                                    on_change=DataState.set_period,
                                    width="100%",
                                ),
                                help_text="Day period between historical data points",
                            ),
                            rx.center(
                                rx.vstack(
                                    rx.text(
                                        "OR", size="1", weight="bold", color="gray"
                                    ),
                                    rx.separator(
                                        orientation="vertical", size="4", height="40px"
                                    ),
                                    align="center",
                                    justify="end",
                                    height="100%",
                                    padding_top="28px",
                                ),
                                width="10%",
                            ),
                            date_range_picker(
                                on_change_start=DataState.set_date_start,
                                value_start=DataState.date_start,
                                on_change_end=DataState.set_date_end,
                                value_end=DataState.date_end,
                                help_text="If set, 'Data Period' selection is ignored.",
                                width="100%",
                            ),
                            width="100%",
                            spacing="4",
                            align="start",
                        ),
                        width="100%",
                        spacing="4",
                    ),
                    rx.spacer(size="4"),
                    rx.hstack(
                        rx.separator(style={"flex": 1}),
                        rx.text("OR", size="4", weight="bold", color="gray"),
                        rx.separator(style={"flex": 1}),
                        width="100%",
                        align="center",
                        padding_y="2",
                    ),
                    form_field(
                        label="Use your own SQL query",
                        control=text_area(
                            value=DataState.sql_query,
                            on_change=DataState.set_sql_query,
                            placeholder="Write your SQL query",
                            rows=4,
                        ),
                    ),
                    form_field(
                        label="Preview Data",
                        control=checkbox_input(
                            label="Enable preview",
                            value=DataState.preview_enabled,
                            on_change=DataState.set_preview_enabled,
                        ),
                    ),
                    rx.hstack(
                        submit_button(
                            on_click=DataState.fetch_data,
                            disabled=DataState.is_loading,
                        ),
                        rx.cond(
                            DataState.is_loading,
                            rx.hstack(
                                rx.spinner(size="3"),
                                rx.text(
                                    "Fetching Data...",
                                    size="3",
                                    color=rx.color("blue", 11),
                                ),
                                cancel_button(on_click=DataState.cancel_fetching),
                                spacing="3",
                                align="center",
                            ),
                            rx.fragment(),
                        ),
                        spacing="4",
                        align="center",
                        width="100%",
                    ),
                    width="100%",
                    spacing="4",
                ),
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        value="manual",
        width="100%",
    )

    ai_tab = rx.tabs.content(
        rx.vstack(
            rx.text("AI-Powered Data Query", size="4", weight="medium"),
            rx.text("Coming soon in the next migration step."),
            spacing="3",
            width="100%",
        ),
        value="ai",
        width="100%",
    )

    tabs = rx.tabs.root(
        rx.tabs.list(
            rx.tabs.trigger("📝 Manual Data Query", value="manual"),
            rx.tabs.trigger("✨ AI-Powered Data Query", value="ai"),
        ),
        manual_tab,
        ai_tab,
        default_value="manual",
        width="100%",
    )

    return page_layout(
        rx.vstack(
            section_header("Data Explorer", "Explore stock data and analytics."),
            tabs,
            _results_view(),
            spacing="4",
            width="100%",
        ),
    )
