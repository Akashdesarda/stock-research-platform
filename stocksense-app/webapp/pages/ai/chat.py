import reflex as rx

from webapp.components.layout import empty_state_card, page_layout, section_header


def chat() -> rx.Component:
    return page_layout(
        section_header("AI Chat"),
        empty_state_card("(Placeholder) Chat UI will be migrated next."),
    )
