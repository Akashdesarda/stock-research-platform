import reflex as rx

from webapp.components.inputs import dropdown_select
from webapp.components.layout import (
    bordered_container,
    page_layout,
    responsive_grid,
    status_indicator,
)
from webapp.state.home import HomeState


def _data_health_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("database", size=20),
                rx.text("Data Health", size="3", weight="bold"),
                spacing="2",
                align="center",
                margin_bottom="2",
            ),
            rx.text(
                "Check the data availability for supported exchanges.",
                size="1",
                color_scheme="gray",
            ),
            rx.divider(),
            rx.vstack(
                dropdown_select(
                    label="Exchange",
                    options=HomeState.data_exchange_options,
                    value=HomeState.selected_status_exchange,
                    on_change=HomeState.set_selected_status_exchange,
                    placeholder="Select Exchange",
                    width="100%",
                ),
                status_indicator(
                    label="Status",
                    value=HomeState.selected_exchange_status,
                    matchers={
                        "OK": ("Up to Date", "green"),
                        "OUTDATED": ("Outdated", "orange"),
                    },
                    default=("No Data", "red"),
                ),
                width="100%",
                spacing="4",
            ),
            align="stretch",
            width="100%",
            spacing="3",
        ),
        size="2",
    )


def _services_health_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("server", size=20),
                rx.text("System Services", size="3", weight="bold"),
                spacing="2",
                align="center",
                margin_bottom="2",
            ),
            rx.text(
                "Operational status of core backend services.",
                size="1",
                color_scheme="gray",
            ),
            rx.divider(),
            rx.vstack(
                status_indicator(
                    label="StockDB API",
                    value=HomeState.stockdb_api,
                    matchers={
                        True: ("Available", "green"),
                        False: ("Unavailable", "red"),
                    },
                ),
                # Add more services here as they grow
                width="100%",
                spacing="3",
            ),
            align="stretch",
            width="100%",
            spacing="3",
        ),
        size="2",
    )


def home() -> rx.Component:
    return page_layout(
        rx.vstack(
            # Main Content
            bordered_container(
                rx.vstack(
                    rx.heading("Welcome to StockSense", size="5"),
                    rx.markdown(
                        """
                        StockSense is your comprehensive platform for stock market research and analysis.

                        **Getting Started:**
                        - Check **Service Status** below to ensure all systems are operational.
                        - Use the **Playground** to explore raw data.
                        - Visit **AI Research** for automated insights.
                        """
                    ),
                    align="start",
                    spacing="3",
                ),
                width="100%",
                align="left",
            ),
            rx.divider(),
            rx.heading("Status", size="5"),
            # Status Dashboard Grid
            # rx.grid(
            responsive_grid(
                _services_health_card(),
                _data_health_card(),
                # We can add more cards here easily
                # columns=rx.breakpoints(initial="1", sm="2", lg="3"),
                spacing="4",
                # width="100%",
            ),
            width="100%",
            spacing="6",
        ),
        on_mount=HomeState.check_input_status,
    )
