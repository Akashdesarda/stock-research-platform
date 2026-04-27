import reflex as rx

from webapp.components.layout import page_layout
from webapp.pages.playground._query_data import (
    _results_view,
    ai_panel,
    manual_panel,
)
from webapp.pages.playground._registered_data import registered_data_panel


def data() -> rx.Component:
    """Playground data workspace."""
    return page_layout(
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger(
                    rx.hstack(
                        rx.icon("user_round_pen", size=20),
                        rx.text("Manual Data Query", size="3"),
                        spacing="2",
                        align="center",
                    ),
                    value="manual",
                ),
                rx.tabs.trigger(
                    rx.hstack(
                        rx.icon("sparkles", size=20),
                        rx.text("AI-Powered Data Query", size="3"),
                        spacing="2",
                        align="center",
                    ),
                    value="ai",
                ),
                rx.tabs.trigger(
                    rx.hstack(
                        rx.icon("table_properties", size=20),
                        rx.text("Registered Datasets", size="3"),
                        spacing="2",
                        align="center",
                    ),
                    value="registered",
                ),
                width="100%",
            ),
            rx.tabs.content(
                rx.vstack(
                    manual_panel(),
                    _results_view(),
                    width="100%",
                    spacing="4",
                ),
                value="manual",
                width="100%",
            ),
            rx.tabs.content(
                rx.vstack(
                    ai_panel(),
                    _results_view(),
                    width="100%",
                    spacing="4",
                ),
                value="ai",
                width="100%",
            ),
            rx.tabs.content(
                registered_data_panel(),
                value="registered",
                width="100%",
            ),
            default_value="manual",
            width="100%",
        )
    )
