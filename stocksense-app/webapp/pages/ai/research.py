import reflex as rx

from webapp.components.layout import page_layout


def research() -> rx.Component:
    return page_layout(
        rx.heading("AI Research", size="7"),
        rx.text("(Placeholder) Research workflow will be migrated next."),
    )
