import reflex as rx

from app.components.common.buttons import my_button
from app.components.interactive import counter_component, item_list_component


def my_page():
    return rx.box(
        rx.text("This is a page"),
        # Reference components defined in other functions.
        my_button(),
    )


def my_div():
    return rx.el.div(
        rx.el.p("Use base html!"),
    )


def learning_page() -> rx.Component:
    """A page to learn Reflex basics with interactive examples."""
    return rx.container(
        rx.vstack(
            rx.heading("🎓 Learning Reflex Basics", size="8", margin_bottom="6"),
            # Introduction section
            rx.box(
                rx.heading("Welcome to Your Learning Journey!", size="6"),
                rx.text(
                    "This page demonstrates basic Reflex concepts. "
                    "Each component below shows different aspects of building web apps with Reflex.",
                    color="gray.600",
                ),
                padding="4",
                background="blue.50",
                border_radius="lg",
                margin_bottom="6",
            ),
            # Interactive components
            counter_component(),
            item_list_component(),
            # Original button (keeping your existing component)
            rx.box(
                rx.heading("Your Original Component", size="6"),
                my_button(),
                padding="4",
                border="1px solid",
                border_color="gray.200",
                border_radius="lg",
            ),
            spacing="6",
            padding="4",
            max_width="800px",
        ),
        center_content=True,
    )
