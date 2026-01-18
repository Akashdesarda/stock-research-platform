"""Simple section sidebar for page navigation."""

import reflex as rx


def nav_sidebar(
    title: str,
    links: list[tuple[str, str]],
) -> rx.Component:
    return rx.box(
        rx.heading(title, size="4"),
        rx.divider(margin_y="0.75rem"),
        rx.vstack(
            *[
                rx.link(
                    rx.button(
                        label,
                        variant="ghost",
                        width="100%",
                        justify_content="flex-start",
                    ),
                    href=href,
                    width="100%",
                )
                for label, href in links
            ],
            width="100%",
            spacing="1",
            align="stretch",
        ),
        border="1px solid var(--gray-6)",
        border_radius="0.75rem",
        padding="0.75rem",
        background_color="var(--gray-2)",
        position="sticky",
        top="5rem",
    )
