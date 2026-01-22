import reflex as rx

from webapp.components.layout import page_layout_with_sidebar
from webapp.components.sidebar import nav_sidebar


def research() -> rx.Component:
    sidebar = nav_sidebar(default_open_group="AI")

    return page_layout_with_sidebar(
        rx.heading("AI Research", size="7"),
        rx.text("(Placeholder) Research workflow will be migrated next."),
        sidebar=sidebar,
    )
