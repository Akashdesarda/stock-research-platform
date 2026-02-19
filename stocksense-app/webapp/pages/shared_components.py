import reflex as rx

from webapp.components.inputs import dropdown_select, multi_select_dropdown
from webapp.components.layout import form_field
from webapp.state.shared import TickerSelectionMixin
from webapp.types import TickerChoice


def _index_based_ticker_selection(state: type[TickerSelectionMixin]) -> rx.Component:
    return dropdown_select(
        label="Select Index",
        options=state.available_index,
        value=state.index_choice,
        on_change=state.set_index_choice,
        disabled=state.ticker_choice != TickerChoice.index.value,
        width="100%",
    )


def _desired_ticker_selection(state: type[TickerSelectionMixin]) -> rx.Component:
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
