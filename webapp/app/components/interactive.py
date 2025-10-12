import reflex as rx

from app.state import GlobalState


def counter_component() -> rx.Component:
    """A simple counter component with increment, decrement, and reset buttons."""
    return rx.vstack(
        rx.heading("Counter example"),
        rx.text(
            f"Current Count: {GlobalState.count}",
            font_size="2rem",
            font_weight="bold",
            color="teal.500",
        ),
        rx.hstack(
            rx.button(
                "➕ Increase",
                on_click=GlobalState.increment,
                color_scheme="teal",
            ),
            rx.button(
                "➖ Decrease",
                on_click=GlobalState.decrement,
                color_scheme="teal",
            ),
            rx.button(
                "🔄 Reset",
                on_click=GlobalState.reset_counter,
                color_scheme="teal",
            ),
            spacing="3",
        ),
        spacing="4",
        align_items="center",
        padding="4",
        border="1px solid",
        border_color="gray.200",
        border_radius="lg",
    )


def item_list_component() -> rx.Component:
    """A component to add items to a list and display them."""
    return rx.vstack(
        rx.heading("Item List Example"),
        rx.hstack(
            rx.input(
                placeholder="Enter an item",
                value=GlobalState.user_input,
                on_change=GlobalState.update_input,
                width="300px",
            ),
            rx.button(
                "Add Item",
                on_click=GlobalState.add_item,
                color_scheme="blue",
            ),
            spacing="3",
        ),
        rx.divider(),
        rx.cond(
            GlobalState.items,
            rx.vstack(
                rx.text("Your Items:", font_weight="bold"),
                rx.foreach(
                    GlobalState.items, lambda item: rx.text(f"• {item}", padding_y="1")
                ),
                spacing="2",
            ),
            rx.text("No items yet. Add some above!", color="gray.500"),
        ),
        spacing="4",
        align="center",
        padding="4",
        border="1px solid",
        border_color="gray.200",
        border_radius="lg",
    )
