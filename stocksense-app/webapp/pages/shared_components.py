from typing import Any

import reflex as rx
import reflex_enterprise as rxe
from reflex.event import EventType

from webapp.components.inputs import dropdown_select, multi_select_dropdown
from webapp.components.layout import form_field, refined_markdown
from webapp.state.shared import ChatMixin, CommonMixin, TickerSelectionMixin
from webapp.types import RunState, TickerChoice, TraceStep


def _index_based_ticker_selection(
    state: type[TickerSelectionMixin],
) -> rx.Component:
    return dropdown_select(
        label="Select Index",
        options=state.available_index,
        value=state.index_choice,
        on_change=state.set_index_choice,
        disabled=state.ticker_choice != TickerChoice.index.value,
        width="100%",
    )


def _desired_ticker_selection(
    state: type[TickerSelectionMixin],
) -> rx.Component:
    return rx.cond(
        state.desired_choice_as_multi_select,
        multi_select_dropdown(
            label="Ticker Symbols",
            options=state.ticker_dropdown_list,
            value=state.selected_ticker_dropdowns,
            on_change=state.get_tickers_for_desired,
            placeholder="Choose options",
            disabled=state.ticker_choice != TickerChoice.desired.value,
            width="100%",
        ),
        dropdown_select(
            label="Ticker Symbols",
            options=state.ticker_dropdown_list,
            value=state.selected_ticker_dropdown,
            on_change=state.get_tickers_for_desired,
            placeholder="Choose options",
            disabled=state.ticker_choice != TickerChoice.desired.value,
            width="100%",
        ),
    )


def _all_ticker_selection() -> rx.Component:
    return rx.callout(
        "All tickers from the selected exchange will be included.",
        color_scheme="blue",
        icon="info",
        width="100%",
    )


def ticker_selector(state: type[TickerSelectionMixin]) -> rx.Component:
    """A reusable ticker selector component.

    Args:
        state: A Reflex State class that inherits from TickerSelectionMixin.
    """
    return rx.vstack(
        rx.text(
            "Exchange and Ticker Selection",
            size="2",
            weight="medium",
            color_scheme="gray",
        ),
        rx.hstack(
            form_field(
                label="Select Exchange",
                control=dropdown_select(
                    label="Select Exchange",
                    options=state.exchange_dropdown_list,
                    value=state.selected_exchange_dropdown,
                    on_change=state.set_exchange_dropdown,
                    placeholder="Choose an exchange",
                    width="100%",
                ),
            ),
            rx.cond(
                state.allow_ticker_choice,
                form_field(
                    label="Ticker Selection Mode",
                    control=dropdown_select(
                        label="Ticker Selection Mode",
                        options=[i.value for i in TickerChoice],
                        value=state.ticker_choice,
                        on_change=state.set_ticker_choice,
                        placeholder="Choose a mode",
                        width="100%",
                    ),
                ),
                rx.fragment(),
            ),
            width="100%",
            spacing="4",
        ),
        rx.match(
            state.ticker_choice,
            (TickerChoice.index.value, _index_based_ticker_selection(state)),
            (TickerChoice.desired.value, _desired_ticker_selection(state)),
            (TickerChoice.all.value, _all_ticker_selection()),
        ),
        width="100%",
        spacing="4",
    )


def workflow_steps(state: type[CommonMixin]) -> rx.Component:
    """Render all trace steps for a non-chat workflow (start -> steps -> finish)."""

    def _step_item(step: TraceStep) -> rx.Component:
        color = rx.cond(step.passed, "green", "red")
        return rxe.mantine.timeline.item(
            rx.text(step.detail, size="1", color=rx.color("gray", 10)),
            title=rx.text(step.name, size="1", weight="bold", color=color),
            bullet=rx.icon(step.icon, size=15),
            color=color,
        )

    return rx.cond(
        state.trace_steps.length() > 0,
        rx.vstack(
            rx.hstack(
                rx.icon(
                    rx.cond(state.steps_open, "chevron_down", "chevron_right"),
                    size=14,
                    color=rx.color("gray", 10),
                ),
                rx.icon("sparkles", size=13, color=rx.color("gray", 10)),
                rx.text(
                    rx.cond(state.steps_open, "Hide steps", "Show steps"),
                    size="1",
                    weight="medium",
                    color=rx.color("gray", 11),
                ),
                spacing="1",
                align="center",
                cursor="pointer",
                on_click=state.toggle_steps,
                padding="4px 8px",
                border_radius="8px",
                _hover={"background": rx.color("gray", 3)},
            ),
            rxe.mantine.collapse(
                rx.box(
                    rxe.mantine.timeline(
                        rx.foreach(state.trace_steps, _step_item),
                        bullet_size=20,
                        line_width=2,
                    ),
                    padding="8px",
                    border_left=f"2px solid {rx.color('gray', 5)}",
                    margin_left="6px",
                ),
                in_=state.steps_open,
            ),
        ),
        rx.fragment(),
    )


def inline_steps(state: type[ChatMixin], msg, index) -> rx.Component:
    def _step_item(step: TraceStep) -> rx.Component:
        color = rx.cond(step.passed, "green", "red")
        return rxe.mantine.timeline.item(
            rx.text(step.detail, size="1", color=rx.color("gray", 10)),
            title=rx.text(step.name, size="1", weight="bold", color=color),
            bullet=rx.icon(step.icon, size=15),
            color=color,
        )

    return rx.cond(
        msg.steps.length() > 0,
        rx.vstack(
            # Compact toggle chip that sits right above the answer text
            rx.hstack(
                rx.icon(
                    rx.cond(msg.steps_open, "chevron_down", "chevron_right"),
                    size=14,
                    color=rx.color("gray", 10),
                ),
                rx.icon("sparkles", size=13, color=rx.color("gray", 10)),
                rx.text(
                    rx.cond(msg.steps_open, "Hide steps", "Show steps"),
                    size="1",
                    weight="medium",
                    color=rx.color("gray", 11),
                ),
                spacing="1",
                align="center",
                cursor="pointer",
                on_click=lambda: state.toggle_message_steps(index),
                padding="4px 8px",
                border_radius="8px",
                _hover={"background": rx.color("gray", 3)},
            ),
            rxe.mantine.collapse(
                rx.box(
                    rxe.mantine.timeline(
                        rx.foreach(msg.steps, _step_item),
                        bullet_size=20,
                        line_width=2,
                    ),
                    padding="8px 4px 4px 8px",
                    border_left=f"2px solid {rx.color('gray', 5)}",
                    margin_left="6px",
                ),
                in_=msg.steps_open,
            ),
            spacing="1",
            width="100%",
            align="start",
        ),
        rx.fragment(),
    )


def _user_bubble(content: str) -> rx.Component:
    return rx.flex(
        rx.box(
            refined_markdown(
                content,
            ),
            background_color=rx.color("accent", 9),
            color="white",
            border_radius="18px 18px 4px 18px",
            padding="8px 14px",  # tighter than before
            max_width="min(75%, 520px)",  # bubble hugs content, capped
            width="fit-content",
            box_shadow="0 1px 2px rgb(0 0 0 / 0.15)",
            style={"word_wrap": "break-word", "white_space": "pre-wrap"},
        ),
        justify="end",
        width="100%",
    )


def _assistant_bubble(state: type[ChatMixin], msg, index) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon("bot", size=16, color=rx.color("accent", 11)),
            background=rx.color("accent", 3),
            border_radius="50%",
            padding="6px",
            margin_top="2px",
            flex_shrink="0",
        ),
        rx.vstack(
            inline_steps(state, msg, index),
            rx.box(
                refined_markdown(msg.content),
                width="100%",
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
        align="start",
        width="100%",
        spacing="3",
    )


def _chat_bubble(state: type[ChatMixin], msg, index) -> rx.Component:
    return rx.cond(
        msg.role == "user",
        _user_bubble(msg.content),
        _assistant_bubble(state, msg, index),
    )


def chat_window(state: type[ChatMixin]) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.foreach(
                state.messages,
                lambda msg, i: _chat_bubble(state, msg, i),
            ),
            width="100%",
            max_width="768px",  # readable column
            margin="0 auto",
            padding_x="16px",
            padding_y="24px",
            spacing="6",  # gap between turns
        ),
        flex="1",
        overflow_y="auto",
        width="100%",
    )


def chat_input(
    state: type[ChatMixin],
    on_submit: EventType[Any],
    on_cancel: EventType[Any],
) -> rx.Component:
    is_generating = state.run_state == RunState.generating.value

    return rx.box(
        rx.hstack(
            rx.text_area(
                value=state.prompt,
                placeholder="Ask StockSense...",
                on_change=state.set_prompt,
                on_key_down=lambda key, modifiers: rx.cond(
                    (key == "Enter") & ~modifiers["shift_key"] & ~is_generating,
                    on_submit.prevent_default,  # block Enter-to-send while generating
                    None,
                ),
                variant="soft",
                border_radius="24px",
                resize="none",
                rows="1",
                key=rx.cond(state.prompt == "", "empty", "filled"),
                auto_height=True,
                width="100%",
                padding_x="1em",
                padding_y="0.75em",
                style={
                    "background": "transparent",
                    "outline": "none",
                    "box_shadow": "none",
                },
            ),
            # ---- SEND / STOP button swap (enum-driven, resume-ready) ----
            rx.cond(
                is_generating,
                # STOP button — cancels the active run
                rx.button(
                    rx.icon("square", size=16),
                    on_click=on_cancel,
                    size="2",
                    radius="full",
                    variant="solid",
                    color_scheme="red",
                    cursor="pointer",
                    margin_right="0.5em",
                    title="Stop generating",
                ),
                # SEND button — submits the prompt
                rx.button(
                    rx.icon("send", size=18),
                    on_click=on_submit,
                    disabled=state.prompt == "",
                    size="2",
                    radius="full",
                    variant="solid",
                    cursor="pointer",
                    margin_right="0.5em",
                    title="Send",
                ),
            ),
            width="100%",
            max_width="768px",
            align_items="center",
            bg=rx.color("gray", 2),
            border=f"1px solid {rx.color('gray', 5)}",
            box_shadow="0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
            border_radius="24px",
            padding_right="0.25em",
        ),
        position="sticky",
        bottom="0",
        width="100%",
        padding="1em",
        backdrop_filter="blur(10px)",
        border_top="1px solid",
        border_color=rx.color("gray", 4),
        z_index="10",
        display="flex",
        justify_content="center",
    )
