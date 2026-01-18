import reflex as rx

from webapp.components.layout import page_layout_with_sidebar
from webapp.components.sidebar import nav_sidebar


def ai() -> rx.Component:
    sidebar = nav_sidebar(
        "AI",
        [
            ("Overview", "/ai"),
            ("Chat", "/ai/chat"),
            ("Research", "/ai/research"),
        ],
    )

    return page_layout_with_sidebar(
        rx.heading("AI", size="7"),
        rx.text("Choose a tool from the sidebar."),
        sidebar=sidebar,
    )
