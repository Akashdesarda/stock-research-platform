import reflex as rx

from webapp.components.layout import page_layout


def strategy() -> rx.Component:
    return page_layout(
        rx.heading("Strategy Playground", size="7"),
        rx.text("(Placeholder) Strategy backtesting UI will be migrated next."),
    )
