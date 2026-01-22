import reflex as rx

from webapp.components.layout import page_layout_with_sidebar
from webapp.components.sidebar import nav_sidebar


def management() -> rx.Component:
    sidebar = nav_sidebar(default_open_group="Management")

    return page_layout_with_sidebar(
        rx.heading("Management", size="7"),
        rx.text("Choose a tool from the sidebar."),
        sidebar=sidebar,
    )
