import reflex as rx

from webapp.components.layout import page_layout_with_sidebar
from webapp.components.sidebar import nav_sidebar


def strategy() -> rx.Component:
    sidebar = nav_sidebar(default_open_group="Playground")

    return page_layout_with_sidebar(
        rx.heading("Playground: Strategy", size="7"),
        rx.text("(Placeholder) Strategy backtesting UI will be migrated next."),
        sidebar=sidebar,
    )
