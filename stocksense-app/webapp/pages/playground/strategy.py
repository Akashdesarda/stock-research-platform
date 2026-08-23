import reflex as rx

from webapp.components.layout import page_layout
from webapp.pages.playground._ai_discovery_strategy import ai_discovery_panel
from webapp.pages.playground._apply_strategy import apply_strategy_panel
from webapp.pages.playground._discovery_strategy import discovery_panel


def strategy() -> rx.Component:
    return page_layout(
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger(
                    rx.hstack(
                        rx.icon("lightbulb", size=20),
                        rx.text("Strategy Discovery", size="3"),
                        spacing="2",
                        align="center",
                    ),
                    value="discovery",
                ),
                rx.tabs.trigger(
                    rx.hstack(
                        rx.icon("sparkles", size=20),
                        rx.text("AI-Powered Strategy Discovery", size="3"),
                        spacing="2",
                        align="center",
                    ),
                    value="ai-discovery",
                ),
                rx.tabs.trigger(
                    rx.hstack(
                        rx.icon("drafting-compass", size=20),
                        rx.text("Apply Strategy", size="3"),
                        spacing="2",
                        align="center",
                    ),
                    value="apply-strategy",
                ),
                size="2",
            ),
            rx.tabs.content(
                discovery_panel(),
                value="discovery",
                width="100%",
                padding_top="1.5rem",
            ),
            rx.tabs.content(
                ai_discovery_panel(),
                value="ai-discovery",
                width="100%",
                padding_top="1.5rem",
            ),
            rx.tabs.content(
                apply_strategy_panel(),
                value="apply-strategy",
                width="100%",
                padding_top="1.5rem",
            ),
            default_value="discovery",
        )
    )
