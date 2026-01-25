import reflex as rx

from webapp.components.layout import page_layout


def management() -> rx.Component:
    return page_layout(
        rx.heading("Management", size="7"),
        rx.text("Choose a tool from the menu."),
    )
