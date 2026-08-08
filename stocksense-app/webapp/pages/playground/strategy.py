import reflex as rx

from webapp.components.layout import page_layout
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
                size="2",
            ),
            rx.tabs.content(
                discovery_panel(),
                value="discovery",
                width="100%",
                padding_top="1.5rem",
            ),
            rx.tabs.content(
                rx.callout(
                    rx.text("Coming soon"),
                    color_scheme="amber",
                ),
                value="ai-discovery",
                width="100%",
                padding_top="1.5rem",
            ),
            default_value="discovery",
            width="100%",
        ),
    )
