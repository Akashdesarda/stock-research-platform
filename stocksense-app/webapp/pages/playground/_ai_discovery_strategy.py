import reflex as rx

from webapp.pages.shared_components import (
    chat_input,
    chat_window,
)
from webapp.state.playground import StrategyAIState
from webapp.types import RunState

_EXAMPLE_PROMPTS = [
    "How is Airtel company in NSE exchange in an uptrend?",
    "Is DMART stock in NSE exchange overbought?",
    "How volatile is TCS company in NSE exchange?",
    "Is Adani green energy company in NSE exchange rally supported by volume?",
]


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
        # chat area (messages + inline steps, or empty-state purpose + examples)
        chat_window(
            StrategyAIState,
            session_agent_id="strategy-selector",
            empty_title="AI-Powered Strategy Discovery",
            empty_description=(
                "Describe the analysis you want, and StockSense will pick a "
                "matching strategy and explain how to use it."
            ),
            example_prompts=_EXAMPLE_PROMPTS,
            on_example=StrategyAIState.submit_example,
        ),
        chat_input(
            StrategyAIState,
            on_submit=StrategyAIState.generate_answer,
            on_cancel=StrategyAIState.cancel_agent_run,
        ),
        width="100%",
        height="100%",
        spacing="4",
    )
