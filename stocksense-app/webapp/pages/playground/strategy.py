import reflex as rx

from webapp.components.layout import page_layout, refined_markdown
from webapp.state.playground import DiscoveryState


def strategy() -> rx.Component:
    return page_layout(
        rx.heading("Strategy Playground", size="7"),
        rx.separator(),
        refined_markdown(DiscoveryState.strategy_index[0]),
    )
