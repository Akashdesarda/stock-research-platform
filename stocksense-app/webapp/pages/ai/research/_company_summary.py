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
        bordered_container(
            rx.vstack(
                ticker_selector(CompanySummaryState),
                rx.separator(size="4", width="100%"),
                submit_button(
                    on_click=CompanySummaryState.generate_summary,
                    disabled=CompanySummaryState.agent_is_generating
                    | (CompanySummaryState.selected_ticker == []),
                ),
                rx.cond(
                    CompanySummaryState.agent_is_generating
                    | (CompanySummaryState.agent_status_message != ""),
                    rx.callout(
                        rx.vstack(
                            rx.hstack(
                                rx.cond(
                                    CompanySummaryState.agent_is_generating,
                                    rx.spinner(size="2"),
                                    rx.icon("check", size=16),
                                ),
                                rx.text(
                                    CompanySummaryState.agent_status_message,
                                    size="2",
                                    weight="medium",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            rx.foreach(
                                CompanySummaryState.agent_steps,
                                lambda step: rx.hstack(
                                    rx.icon("check", size=16, color="green"),
                                    rx.text(step, size="2", color="gray"),
                                    spacing="2",
                                    align="center",
                                ),
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        icon="sparkles",
                        color_scheme="blue",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    (CompanySummaryState.agent_error != "")
                    & (CompanySummaryState.agent_is_generating is False),
                    rx.callout(
                        CompanySummaryState.agent_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
            )
        ),
        chat_window(CompanySummaryState),
        rx.cond(
            CompanySummaryState.summary_result != "",
            chat_input(CompanySummaryState),
            rx.fragment(),
        ),
    )
