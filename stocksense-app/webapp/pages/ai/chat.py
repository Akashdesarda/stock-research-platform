import reflex as rx

from webapp.components.layout import page_layout


def chat() -> rx.Component:
    return page_layout(
        rx.heading("AI Chat", size="7"),
        rx.text("(Placeholder) Chat UI will be migrated next."),
    )
