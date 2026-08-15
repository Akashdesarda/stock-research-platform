import reflex as rx

from webapp.components.layout import empty_state_card, page_layout, section_header


def ai() -> rx.Component:
    return page_layout(
        section_header("AI"),
        empty_state_card("Choose a tool from the menu."),
    )
