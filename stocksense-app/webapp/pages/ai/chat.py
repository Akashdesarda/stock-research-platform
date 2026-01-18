import reflex as rx

from webapp.components.layout import page_layout_with_sidebar
from webapp.components.sidebar import nav_sidebar


def chat() -> rx.Component:
    sidebar = nav_sidebar(
        "AI",
        [
            ("Overview", "/ai"),
            ("Chat", "/ai/chat"),
            ("Research", "/ai/research"),
        ],
    )

    return page_layout_with_sidebar(
        rx.heading("AI Chat", size="7"),
        rx.text("(Placeholder) Chat UI will be migrated next."),
        sidebar=sidebar,
    )
