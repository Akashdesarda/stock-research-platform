import reflex as rx

from webapp.components.layout import page_layout_with_sidebar
from webapp.components.sidebar import nav_sidebar


def playground() -> rx.Component:
    sidebar = nav_sidebar(
        "Playground",
        [
            ("Overview", "/playground"),
            ("Data", "/playground/data"),
            ("Strategy", "/playground/strategy"),
        ],
    )

    return page_layout_with_sidebar(
        rx.heading("Playground", size="7"),
        rx.text("Choose a tool from the sidebar."),
        sidebar=sidebar,
    )
