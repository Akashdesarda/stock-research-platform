"""Common app layout (navbar + container)."""

import reflex as rx


def navbar() -> rx.Component:
    def nav_link(label: str, href: str) -> rx.Component:
        return rx.link(
            rx.button(label, variant="ghost"),
            href=href,
        )

    return rx.box(
        rx.hstack(
            rx.heading("StockSense", size="5"),
            rx.spacer(),
            nav_link("Home", "/"),
            nav_link("Playground", "/playground"),
            nav_link("AI", "/ai"),
            nav_link("Management", "/management"),
            rx.color_mode.button(),
            align="center",
            width="100%",
        ),
        width="100%",
        padding_y="0.75rem",
        padding_x="1rem",
        border_bottom="1px solid var(--gray-6)",
    )


def page_layout(*children: rx.Component) -> rx.Component:
    return page_layout_with_sidebar(*children, sidebar=None)


def page_layout_with_sidebar(
    *children: rx.Component,
    sidebar: rx.Component | None,
) -> rx.Component:
    content = (
        rx.hstack(
            rx.box(sidebar, min_width="14rem", max_width="14rem"),
            rx.box(*children, width="100%"),
            align="start",
            width="100%",
            spacing="6",
        )
        if sidebar is not None
        else rx.box(*children)
    )

    return rx.box(
        navbar(),
        rx.container(
            rx.box(content, padding_top="1.25rem"),
            # Responsive container: expands on large screens, stays readable on small.
            max_width="clamp(64rem, 92vw, 96rem)",
        ),
        width="100%",
    )


def form_field(
    label: str, control: rx.Component, help_text: str | None = None
) -> rx.Component:
    return rx.vstack(
        rx.spacer(spacing="2"),
        rx.hstack(
            rx.text(label, weight="medium"),
            rx.cond(
                help_text is None,
                rx.fragment(),
                rx.tooltip(
                    rx.icon(
                        "circle_help",
                        stroke_width=2,
                        size=18,
                        style={"verticalAlign": "middle"},
                    ),
                    content=help_text,
                ),
            ),
            align="center",
            width="100%",
            justify="between",
            spacing="2",
            gap="2em",
            wrap="wrap",
        ),
        control,
        width="100%",
        spacing="3",
    )


def bordered_container(
    *children,
    width: str | dict = "100%",
    max_width: str = "1200px",
    align: str = "center",
    padding: str = "24px",  # Explicit pixel value for clarity
    background: str = "transparent",
    **props,
):
    # Mapping alignment to margin logic
    margin_map = {
        "left": {"margin_left": "0", "margin_right": "auto"},
        "center": {"margin_left": "auto", "margin_right": "auto"},
        "right": {"margin_left": "auto", "margin_right": "0"},
    }
    alignment_styles = margin_map.get(align, margin_map["center"])

    return rx.box(
        # We wrap children in a vstack to force vertical spacing (gap)
        rx.vstack(
            *children,
            align_items="stretch",  # Ensures children fill the width of the padding
            spacing="4",  # This creates the gap BETWEEN children
        ),
        # Box styles
        width=width,
        max_width=max_width,
        padding=padding,  # This creates the gap BETWEEN border and children
        background_color=background,
        border=f"1px solid {rx.color('gray', 5)}",
        border_radius="12px",
        **alignment_styles,
        **props,
    )


def stat_card(label: str, value: str, trend: str | None = None, icon: str = "activity"):
    """Displays a key metric with an optional trend indicator."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=20, color=rx.color("gray", 10)),
                rx.text(label, size="2", color=rx.color("gray", 11)),
                spacing="2",
                align="center",
            ),
            rx.hstack(
                rx.heading(value, size="6"),
                rx.badge(trend, color_scheme="green") if trend else rx.fragment(),
                justify="between",
                width="100%",
                align="end",
            ),
            spacing="1",
        ),
        width="100%",
    )


def section_header(
    title: str, subtitle: str | None = None, action_button: rx.Component | None = None
) -> rx.Component:
    """A standardized header for page sections."""
    return rx.hstack(
        rx.vstack(
            rx.heading(title, size="6"),
            rx.text(subtitle, size="2", color=rx.color("gray", 11))
            if subtitle
            else rx.fragment(),
            spacing="1",
        ),
        rx.spacer(),
        action_button or rx.fragment(),
        width="100%",
        padding_y="4",
        border_bottom=f"1px solid {rx.color('gray', 4)}",
        align="end",
    )


def responsive_grid(*children, columns=None, spacing="4"):
    """A layout wrapper that adjusts columns based on screen size."""
    if columns is None:
        columns = [1, 2, 3]
    return rx.grid(
        *children,
        columns={
            "sm": str(columns[0]),
            "md": str(columns[1] if len(columns) > 1 else columns[0]),
            "lg": str(columns[2] if len(columns) > 2 else columns[1]),
        },
        spacing=spacing,
        width="100%",
    )
