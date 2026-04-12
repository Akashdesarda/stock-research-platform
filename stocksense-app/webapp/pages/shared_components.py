import reflex as rx

from webapp.components.inputs import dropdown_select, multi_select_dropdown
from webapp.components.layout import form_field
from webapp.state.shared import ChatMixin, TickerSelectionMixin
from webapp.types import TickerChoice


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
    # NOTE - # No selection needed for "All" option
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


def chat_bubble(role: str, content: str) -> rx.Component:
    is_user = role == "user"

    return rx.hstack(
        rx.box(
            rx.markdown(content),
            background_color=rx.cond(
                is_user, rx.color("accent"), "transparent"
            ),
            border_radius="10px",
            max_width="80%",
            margin="16px",
            padding="10px",
        ),
        justify=rx.cond(is_user, "end", "start"),
        width="100%",
        # padding_y="0.25em",
    )


def chat_window(state: type[ChatMixin]) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.foreach(
                state.messages,
                lambda msg: chat_bubble(msg.role, msg.content),
            ),
            width="100%",
            padding_x="24px",
            padding_y="20px",
            spacing="3",
        ),
        flex="1",
        overflow_y="auto",
        width="100%",
    )


def chat_input(state: type[ChatMixin]) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text_area(
                value=state.prompt,
                placeholder="Ask StockSense...",
                on_change=state.set_prompt,
                on_key_down=lambda key, modifiers: rx.cond(
                    (key == "Enter") & ~modifiers["shift_key"],
                    state.generate_answer.prevent_default,
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
            rx.button(
                rx.icon("send", size=18),
                on_click=state.generate_answer,
                loading=state.is_loading,
                disabled=state.is_loading | (state.prompt == ""),
                size="2",
                radius="full",
                variant="solid",
                cursor="pointer",
                margin_right="0.5em",
            ),
            width="100%",
            max_width="900px",
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
