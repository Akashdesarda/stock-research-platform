from typing import Any, Literal

import reflex as rx

from webapp.components.navbar import navbar


def page_layout(*children: rx.Component, **props) -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            rx.box(*children, padding_top="1.25rem"),
            width="100%",
            padding_x="1.5em",
            padding_bottom="2em",
        ),
        width="100%",
        **props,
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
    # Map alignment to margins. Use style dict to avoid passing unsupported kwargs.
    margin_map = {
        "left": {"marginLeft": "0", "marginRight": "auto"},
        "center": {"marginLeft": "auto", "marginRight": "auto"},
        "right": {"marginLeft": "auto", "marginRight": "0"},
    }
    alignment_style = margin_map.get(align, margin_map["center"])

    user_style = props.pop("style", {}) or {}
    merged_style = {**user_style, **alignment_style}

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
        style=merged_style,
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


def status_indicator(
    label: str,
    value: Any,
    matchers: dict[Any, tuple[str, str]],
    default: tuple[str, str] = ("Unknown", "gray"),
) -> rx.Component:
    """
    Displays a label on the left and a conditional badge on the right.

    Args:
        label: The text label.
        value: The state var to check.
        matchers: Dict mapping value to (badge_text, badge_color).
        default: Fallback (badge_text, badge_color) if no match.
    """
    badge_component = rx.badge(default[0], color_scheme=default[1], variant="surface")

    # Build the nested rx.cond structure
    for match_value, (badge_text, badge_color) in matchers.items():
        badge_component = rx.cond(
            value == match_value,
            rx.badge(badge_text, color_scheme=badge_color, variant="surface"),
            badge_component,
        )

    return rx.hstack(
        rx.text(label, size="2", weight="medium"),
        badge_component,
        width="100%",
        justify="between",
        align="center",
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


def responsive_grid(
    *children,
    columns=None,
    spacing: Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"] = "4",
):
    """A layout wrapper that adjusts columns based on screen size."""
    if columns is None:
        columns = [1, 2, 3]
    return rx.grid(
        *children,
        columns=rx.breakpoints(
            sm=str(columns[0]),
            md=str(columns[1] if len(columns) > 1 else columns[0]),
            lg=str(columns[2] if len(columns) > 2 else columns[1]),
        ),
        spacing=spacing,
        width="100%",
    )
