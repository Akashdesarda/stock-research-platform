import reflex as rx

from webapp.components.layout import page_layout
from webapp.state import State


def home() -> rx.Component:
    return page_layout(
        rx.vstack(
            rx.markdown(
                """
StockSense is a comprehensive platform for stock market research and analysis. It provides
tools and data to help investors make informed decisions.
""".strip()
            ),
            rx.divider(margin_y="0.75rem"),
            rx.heading("Demo: Central State", size="5"),
            rx.text(State.greeting, color_scheme="gray"),
            rx.hstack(
                rx.button("-", on_click=State.decrement, variant="outline"),
                rx.badge(State.counter, variant="soft"),
                rx.button("+", on_click=State.increment),
                rx.button("Reset", on_click=State.reset_counter, variant="ghost"),
                spacing="3",
                align="center",
                wrap="wrap",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text("Your name"),
                    rx.input(
                        value=State.name,
                        on_change=State.set_name,
                        placeholder="Type your name",
                        width="100%",
                    ),
                    width="100%",
                    spacing="2",
                ),
                rx.vstack(
                    rx.text("Exchange"),
                    rx.select(
                        State.exchanges,
                        value=State.selected_exchange,
                        on_change=State.set_selected_exchange,
                        placeholder="Select exchange",
                        width="100%",
                    ),
                    width="100%",
                    spacing="2",
                ),
                width="100%",
                spacing="6",
                align="end",
            ),
            rx.divider(margin_y="0.75rem"),
            rx.heading("Demo: Async httpx call", size="5"),
            rx.text(
                "Clicks run an async Reflex event that fetches from https://httpbin.org using httpx.",
                color_scheme="gray",
            ),
            rx.hstack(
                rx.button(
                    "Fetch httpbin (async)",
                    on_click=State.fetch_httpbin,
                ),
                rx.cond(
                    State.httpbin_is_loading,
                    rx.badge("Loading...", variant="soft"),
                    rx.badge("Idle", variant="soft"),
                ),
                spacing="3",
                align="center",
                wrap="wrap",
                width="100%",
            ),
            rx.cond(
                State.httpbin_error != "",
                rx.callout(
                    State.httpbin_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
                rx.fragment(),
            ),
            rx.cond(
                State.has_httpbin_response,
                rx.vstack(
                    rx.hstack(
                        rx.text("Status: ", State.httpbin_status_code),
                        rx.text("Origin: ", State.httpbin_origin),
                        spacing="6",
                        wrap="wrap",
                        width="100%",
                    ),
                    rx.text("URL: ", State.httpbin_url),
                    rx.text("User-Agent: ", State.httpbin_user_agent),
                    rx.text("Last fetched (UTC): ", State.httpbin_last_fetched_utc),
                    rx.code_block(
                        State.httpbin_response_json,
                        language="json",
                        width="100%",
                    ),
                    width="100%",
                    spacing="2",
                ),
                rx.fragment(),
            ),
            width="100%",
            spacing="4",
        )
    )
