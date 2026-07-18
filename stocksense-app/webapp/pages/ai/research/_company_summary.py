import reflex as rx

from webapp.components.inputs import submit_button
from webapp.components.layout import bordered_container
from webapp.pages.shared_components import (
    chat_input,
    chat_window,
    ticker_selector,
)
from webapp.state.ai import CompanySummaryState


def company_summary_component() -> rx.Component:
    return rx.vstack(
        # ---------- TICKER SELECTION FORM ----------
        bordered_container(
            rx.vstack(
                ticker_selector(CompanySummaryState),
                rx.separator(size="4", width="100%"),
                submit_button(
                    on_click=CompanySummaryState.generate_summary,
                    disabled=CompanySummaryState.agent_is_generating
                    | (CompanySummaryState.selected_ticker == []),
                ),
                # Lightweight live status line (spinner + message) — NOT the steps.
                # The detailed trace steps now live inside each assistant bubble.
                rx.cond(
                    CompanySummaryState.agent_is_generating
                    | (CompanySummaryState.agent_status_message != ""),
                    rx.hstack(
                        rx.cond(
                            CompanySummaryState.agent_is_generating,
                            rx.spinner(size="2"),
                            rx.icon("check", size=16, color="green"),
                        ),
                        rx.text(
                            CompanySummaryState.agent_status_message,
                            size="2",
                            weight="medium",
                            color=rx.color("gray", 11),
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                # Error callout (only when not actively generating)
                rx.cond(
                    (CompanySummaryState.agent_error != "")
                    & (CompanySummaryState.agent_is_generating == False),  # noqa: E712
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
        # ---------- CHAT AREA (messages + inline steps) ----------
        chat_window(CompanySummaryState),
        # ---------- INPUT (only after first summary exists) ----------
        rx.cond(
            CompanySummaryState.summary_result != "",
            chat_input(
                CompanySummaryState, on_submit=CompanySummaryState.generate_answer
            ),
            rx.fragment(),
        ),
        width="100%",
        height="100%",
        spacing="4",
    )
