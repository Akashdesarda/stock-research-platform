import reflex as rx
import reflex_enterprise as rxe
from stocksense.types import DataInterval, DataPeriod

from webapp.components.inputs import (
    cancel_button,
    checkbox_input,
    date_range_picker,
    dropdown_select,
    submit_button,
    text_area,
)
from webapp.components.layout import (
    bordered_container,
    form_field,
    page_layout,
    section_header,
)
from webapp.pages.shared_components import ticker_selector
from webapp.state.playground import DataState


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
    """Playground --> Data page"""
    tabs_list = (
        rx.tabs.list(
            rx.tabs.trigger(
                rx.hstack(
                    rx.icon("user_round_pen", size=20),
                    rx.text("Manual Data Query", size="3"),
                ),
                value="manual",
            ),
            rx.tabs.trigger(
                rx.hstack(
                    rx.icon("sparkles", size=20),
                    rx.text("AI-Powered Data Query", size="3"),
                ),
                value="ai",
            ),
        ),
    )

    manual_tab = rx.tabs.content(
        bordered_container(
            rx.vstack(
                # exch, tkr selection --> query params --> OR --> sql query --> submit
                # SECTION - Exchange and Ticker
                ticker_selector(DataState),
                rx.separator(size="4", width="100%"),
                # SECTION - Time Range
                rx.vstack(  # interval --> period/date range
                    rx.spacer(),
                    rx.text(
                        "Time Range Selection",
                        size="2",
                        weight="medium",
                        color_scheme="gray",
                    ),
                    rx.hstack(  # interval + separator
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
                    rx.hstack(  # OR separator + period/date range
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
                        rx.center(  # OR separator
                            rx.vstack(
                                rx.text("OR", size="1", weight="bold", color="gray"),
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
                        # date range picker
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
                rx.hstack(  # OR separator
                    rx.separator(style={"flex": 1}),
                    rx.text("OR", size="4", weight="bold", color="gray"),
                    rx.separator(style={"flex": 1}),
                    width="100%",
                    align="center",
                    padding_y="2",
                ),
                form_field(  # sql query input
                    label="Use your own SQL query",
                    control=text_area(
                        value=DataState.sql_query,
                        on_change=DataState.set_sql_query,
                        placeholder="Write your SQL query",
                        rows=4,
                    ),
                ),
                rx.spacer(),
                checkbox_input(
                    label="Enable data preview",
                    value=DataState.preview_enabled,
                    on_change=DataState.set_preview_enabled,
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
        tabs_list,
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
