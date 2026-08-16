from typing import Any

import reflex as rx
import reflex_enterprise as rxe
from reflex.event import EventType

from webapp.components.inputs import dropdown_select, multi_select_dropdown
from webapp.components.layout import (
    form_field,
    refined_markdown,
    subsection_header,
    tooltip_external_link,
)
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
        subsection_header("Exchange and Ticker Selection"),
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
                on_click=state.toggle_message_steps(index),
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


def _session_links(agent_id: str, type: str = "agent") -> rx.Component:
    """External Agno OS links scoped to the page's agent."""
    return rx.hstack(
        tooltip_external_link(
            "Past chats",
            f"https://os.agno.com/chat/?type={type}&id={agent_id}",
            icon="history",
            tooltip="Access & continue conversation in past chats",
        ),
        tooltip_external_link(
            label="Sessions",
            href="https://os.agno.com/sessions",
            icon="folders",
            tooltip="Manage all the past sessions",
        ),
        spacing="4",
        align="center",
        justify="end",
        width="100%",
        padding_top="8px",
        padding_bottom="4px",
    )


def _chat_empty_state(
    state: type[ChatMixin],
    *,
    empty_title: str | None,
    empty_description: str | None,
    example_prompts: list[str] | None,
    on_example: EventType[str] | None,
) -> rx.Component:
    """Centered purpose + clickable example prompts when the conversation is empty."""
    prompts = example_prompts or []

    def _example_button(text: str) -> rx.Component:
        if on_example is not None:
            click_handler = on_example(text)
        else:
            click_handler = state.set_prompt(text)
        return rx.button(
            text,
            on_click=click_handler,
            size="1",
            variant="soft",
            radius="medium",
            cursor="pointer",
            white_space="normal",
            height="auto",
            padding_y="0.4em",
            padding_x="0.75em",
            text_align="left",
            style={"font_weight": 400, "line_height": 1.45},
        )

    children: list[rx.Component] = []
    if empty_title:
        children.append(
            rx.heading(empty_title, size="4", weight="medium", text_align="center")
        )
    if empty_description:
        children.append(
            rx.text(
                empty_description,
                size="2",
                weight="regular",
                color=rx.color("gray", 11),
                text_align="center",
                max_width="28rem",
                line_height="1.5",
            )
        )
    if prompts:
        children.append(
            rx.vstack(
                *[_example_button(p) for p in prompts],
                spacing="1",
                width="100%",
                max_width="24rem",
                align="stretch",
            )
        )

    return rx.center(
        rx.vstack(
            *children,
            spacing="3",
            align="center",
            width="100%",
        ),
        width="100%",
        min_height="12rem",
        padding="1.25rem",
    )


def chat_window(
    state: type[ChatMixin],
    *,
    session_agent_id: str,
    empty_title: str | None = None,
    empty_description: str | None = None,
    example_prompts: list[str] | None = None,
    on_example: EventType[str] | None = None,
) -> rx.Component:
    has_empty_state = bool(empty_title or empty_description or example_prompts)
    message_list = rx.vstack(
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
    )

    content = (
        rx.cond(
            state.messages.length() == 0,
            _chat_empty_state(
                state,
                empty_title=empty_title,
                empty_description=empty_description,
                example_prompts=example_prompts,
                on_example=on_example,
            ),
            message_list,
        )
        if has_empty_state
        else message_list
    )

    return rx.box(
        rx.vstack(
            _session_links(session_agent_id),
            content,
            spacing="0",
            width="100%",
            height="100%",
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
            # New chat — native to all chat_input consumers via ChatMixin.reset_chat
            rx.cond(
                state.messages.length() > 0,
                rx.button(
                    rx.icon("message-square-plus", size=16),
                    on_click=state.reset_chat,
                    disabled=is_generating,
                    size="2",
                    radius="full",
                    variant="soft",
                    cursor=rx.cond(is_generating, "not-allowed", "pointer"),
                    margin_left="0.5em",
                    title="New chat",
                ),
                rx.fragment(),
            ),
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
        z_index="10",
        display="flex",
        justify_content="center",
    )
