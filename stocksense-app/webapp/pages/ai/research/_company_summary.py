import reflex as rx

from webapp.components.inputs import checkbox_input, submit_button
from webapp.components.layout import bordered_container
from webapp.pages.shared_components import ticker_selector
from webapp.state.ai import CompanySummaryState


def company_summary_component() -> rx.Component:
    return rx.vstack(
        bordered_container(
            rx.vstack(
                ticker_selector(CompanySummaryState),
                rx.separator(size="4", width="100%"),
                checkbox_input(
                    label="Use cached (if available)",
                    value=CompanySummaryState.ai_use_cache,
                    on_change=CompanySummaryState.set_ai_use_cache,
                ),
                submit_button(
                    on_click=[
                        CompanySummaryState.set_ai_prompt,
                        CompanySummaryState.get_summary,
                    ],
                    disabled=CompanySummaryState.ai_is_generating
                    | (CompanySummaryState.selected_exchange == "")
                    | (CompanySummaryState.selected_ticker[0] == ""),
                ),
                rx.cond(
                    CompanySummaryState.ai_is_generating
                    | (CompanySummaryState.ai_status_message != ""),
                    rx.callout(
                        rx.vstack(
                            rx.hstack(
                                rx.cond(
                                    CompanySummaryState.ai_is_generating,
                                    rx.spinner(size="2"),
                                    rx.icon("check", size=16),
                                ),
                                rx.text(
                                    CompanySummaryState.ai_status_message,
                                    size="2",
                                    weight="medium",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            rx.foreach(
                                CompanySummaryState.ai_status_steps,
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
                    (CompanySummaryState.ai_error != "")
                    & (CompanySummaryState.ai_is_generating is False),
                    rx.callout(
                        CompanySummaryState.ai_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
            )
        ),
        rx.cond(
            CompanySummaryState.summary_result != "",
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("sparkles", color=rx.color("accent", 9)),
                        rx.text(
                            "AI Summary",
                            weight="bold",
                            color=rx.color("accent", 11),
                        ),
                        align="center",
                        spacing="2",
                        margin_bottom="1em",
                    ),
                    rx.markdown(
                        CompanySummaryState.summary_result,
                        component_map={
                            "p": lambda text: rx.text(
                                text, margin_bottom="1em", line_height="1.6"
                            ),
                        },
                    ),
                    align_items="stretch",
                    width="100%",
                ),
                # Making the box chat bubble like & scrollable
                padding="2em",
                background=rx.color("gray", 3),
                border_radius="12px",
                width="100%",
            ),
            rx.fragment(),
        ),
    )
