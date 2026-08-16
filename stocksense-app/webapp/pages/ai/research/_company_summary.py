import reflex as rx

from webapp.components.inputs import submit_button
from webapp.components.layout import bordered_container
from webapp.pages.shared_components import (
    chat_input,
    chat_session_history_button,
    chat_window,
    session_history_drawer,
    ticker_selector,
)
from webapp.state.ai import CompanySummaryState
from webapp.types import RunState


def company_summary_component() -> rx.Component:
    return rx.vstack(
        session_history_drawer(CompanySummaryState),
        bordered_container(
            rx.vstack(
                #  ticker selection form
                ticker_selector(CompanySummaryState),
                rx.separator(size="4", width="100%"),
                rx.hstack(
                    submit_button(
                        on_click=CompanySummaryState.generate_summary,
                        disabled=(
                            CompanySummaryState.run_state == RunState.generating.value
                        )
                        | (CompanySummaryState.selected_ticker == []),
                    ),
                    # History is available before chat_input mounts (gated on summary).
                    rx.cond(
                        CompanySummaryState.summary_result == "",
                        chat_session_history_button(CompanySummaryState),
                        rx.fragment(),
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                # Error callout (only when not actively generating)
                rx.cond(
                    (CompanySummaryState.agent_error != "")
                    & (CompanySummaryState.run_state != RunState.generating.value),
                    rx.callout(
                        CompanySummaryState.agent_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                spacing="4",
                width="100%",
            )
        ),
        # chat area (messages + inline steps, or empty-state purpose)
        chat_window(
            CompanySummaryState,
            empty_title="Company Summary",
            empty_description=(
                "Select a ticker and generate a summary, then ask follow-up "
                "questions here."
            ),
        ),
        # chat input (only after first summary exists)
        rx.cond(
            CompanySummaryState.summary_result != "",
            chat_input(
                CompanySummaryState,
                on_submit=CompanySummaryState.generate_answer,
                on_cancel=CompanySummaryState.cancel_agent_run,
                include_session_drawer=False,
            ),
            rx.fragment(),
        ),
        width="100%",
        height="100%",
        spacing="4",
    )
