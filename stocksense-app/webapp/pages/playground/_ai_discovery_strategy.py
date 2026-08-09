import reflex as rx

from webapp.pages.shared_components import (
    chat_input,
    chat_window,
)
from webapp.state.playground import StrategyAIState
from webapp.types import RunState


def ai_discovery_panel() -> rx.Component:
    return rx.vstack(
        rx.cond(
            (StrategyAIState.agent_error != "")
            & (StrategyAIState.run_state != RunState.generating.value),
            rx.callout(
                StrategyAIState.agent_error,
                icon="triangle_alert",
                color_scheme="red",
                width="100%",
            ),
            rx.fragment(),
        ),
        # chat area (messages + inline steps)
        chat_window(StrategyAIState),
        chat_input(
            StrategyAIState,
            on_submit=StrategyAIState.generate_answer,
            on_cancel=StrategyAIState.cancel_agent_run,
        ),
        width="100%",
        height="100%",
        spacing="4",
    )
