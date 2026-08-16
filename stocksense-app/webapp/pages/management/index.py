import reflex as rx

from webapp.components.layout import empty_state_card, page_layout, section_header


def management() -> rx.Component:
    return page_layout(
        section_header("Management"),
        empty_state_card("Choose a tool from the menu."),
    )
