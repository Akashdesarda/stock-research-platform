from typing import Any, Literal

import polars as pl
import reflex as rx
import reflex_enterprise as rxe

from webapp.components.navbar import navbar


def page_layout(*children: rx.Component, **props) -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            rx.box(
                *children,
                width="100%",
                max_width="1200px",
                margin_x="auto",
                padding_top="1.25rem",
            ),
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
    title: str | rx.Var,
    subtitle: str | rx.Var | None = None,
    action_button: rx.Component | None = None,
) -> rx.Component:
    """A standardized header for page sections."""
    return rx.hstack(
        rx.vstack(
            rx.heading(title, size="6"),
            rx.text(subtitle, size="2", color=rx.color("gray", 11))
            if subtitle is not None
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


def dialog_actions(
    *,
    on_submit=None,
    on_cancel=None,
    submit_label: str = "Submit",
    cancel_label: str = "Cancel",
    wrap_submit_in_close: bool = False,
    wrap_cancel_in_close: bool = False,
) -> rx.Component:
    """Reusable dialog action row with consistent cancel/submit buttons."""
    submit_component = rx.button(
        submit_label,
        radius="large",
        color_scheme="blue",
        size="2",
        on_click=on_submit,
    )
    cancel_component = rx.button(
        cancel_label,
        radius="large",
        color_scheme="red",
        size="2",
        variant="soft",
        on_click=on_cancel,
    )

    if wrap_submit_in_close:
        submit_component = rx.dialog.close(submit_component)

    if wrap_cancel_in_close:
        cancel_component = rx.dialog.close(cancel_component)

    return rx.hstack(
        cancel_component,
        submit_component,
        spacing="3",
        justify="end",
        width="100%",
    )


def dialog_form(
    *fields: rx.Component,
    title: str | rx.Var,
    description: str | rx.Var | None = None,
    trigger: rx.Component | None = None,
    actions: rx.Component | None = None,
    max_width: str = "560px",
    **root_props,
) -> rx.Component:
    """Reusable dialog root + content layout for consistent modal forms."""
    children = []

    if trigger is not None:
        children.append(rx.dialog.trigger(trigger))

    children.append(
        rx.dialog.content(
            rx.dialog.title(title),
            rx.cond(
                description is None,
                rx.fragment(),
                rx.dialog.description(description),
            ),
            rx.vstack(
                *fields,
                actions or rx.fragment(),
                spacing="4",
                width="100%",
            ),
            max_width=max_width,
        )
    )

    return rx.dialog.root(
        *children,
        **root_props,
    )


def responsive_grid(
    *children,
    columns=None,
    spacing: Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"] = "4",
    **props,
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
        **props,
    )


def data_preview(data: pl.DataFrame, **props) -> rx.Component:
    # Setting appropriate defaults for props
    width = props.pop("width", "100%")
    max_width = props.pop("max_width", "1200px")
    height = props.pop("height", "400px")

    polars_to_ag_grid_filter_type_map = {
        pl.Int64: rxe.ag_grid.filters.number,
        pl.Float64: rxe.ag_grid.filters.number,
        pl.String: rxe.ag_grid.filters.text,
        pl.Boolean: rxe.ag_grid.filters.text,
        pl.Date: rxe.ag_grid.filters.date,
        pl.Datetime: rxe.ag_grid.filters.date,
    }
    schema = data.schema

    column_def = [
        {
            "field": col,
            "filter": polars_to_ag_grid_filter_type_map[schema[col]],
            "sortable": True,
        }
        for col in schema
    ]
    return rxe.ag_grid(
        id="change with uuid",
        row_data=data.to_dicts(),
        column_defs=column_def,
        pagination=True,
        pagination_page_size=10,
        pagination_page_size_selector=[10, 40, 100],
        width=width,
        max_width=max_width,
        height=height,
        **props,
    )


def _h(size, mt, mb):
    return lambda text: rx.heading(
        text,
        size=size,
        margin_top=mt,
        margin_bottom=mb,
        line_height="1.3",
    )


def refined_markdown(content, **props) -> rx.Component:
    _cell_border = f"1px solid {rx.color('gray', 5)}"
    markdown_component_map = {
        # markdown header support
        "h1": _h("6", "1em", "0.5em"),
        "h2": _h("5", "0.9em", "0.4em"),
        "h3": _h("4", "0.8em", "0.35em"),
        "h4": _h("3", "0.7em", "0.3em"),
        # markdown paragraph and list support
        "p": lambda text: rx.text(
            text,
            margin_bottom="0.75em",
            line_height="1.7",
            size="3",
        ),
        "li": lambda text: rx.list_item(
            text,
            margin_bottom="0.35em",
            line_height="1.6",
        ),
        "ul": lambda items: rx.list.unordered(
            items,
            margin_bottom="0.75em",
            padding_left="1.25em",
            spacing="1",
        ),
        "ol": lambda items: rx.list.ordered(
            items,
            margin_bottom="0.75em",
            padding_left="1.25em",
            spacing="1",
        ),
        # markdown code support
        "code": lambda text: rx.code(text, color_scheme="gray"),
        "codeblock": lambda text, **props: rx.code_block(
            text,
            **props,
            margin_y="0.75em",
            border_radius="8px",
            wrap_long_lines=True,
        ),
        # markdown quote support
        "a": lambda text, **props: rx.link(text, **props, color_scheme="blue"),
        "blockquote": lambda text: rx.box(
            rx.text(text, size="3", color=rx.color("gray", 11)),
            border_left=f"3px solid {rx.color('accent', 7)}",
            padding_left="1em",
            margin_y="0.75em",
        ),
        # markdown table support
        "table": lambda children: rx.box(
            rx.table.root(children, variant="surface", size="1", width="100%"),
            overflow_x="auto",
            margin_y="1em",
            width="100%",
            border=f"1px solid {rx.color('gray', 6)}",
            border_radius="8px",
        ),
        "thead": lambda children: rx.table.header(children),
        "tbody": lambda children: rx.table.body(children),
        "tr": lambda children: rx.table.row(children),
        "th": lambda text: rx.table.column_header_cell(
            text,
            style={
                "white_space": "nowrap",
                "border_right": _cell_border,  # vertical column separator
            },
        ),
        "td": lambda text: rx.table.cell(
            text,
            style={
                "border_right": _cell_border,  # vertical column separator
            },
        ),
    }

    return rx.markdown(content, component_map=markdown_component_map, **props)
