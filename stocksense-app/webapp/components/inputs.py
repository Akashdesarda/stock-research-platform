from typing import Any, Callable, Literal, Sequence

import reflex as rx
import reflex_enterprise as rxe
from reflex.event import EventType
from reflex.vars import ArrayVar
from reflex.vars.base import AsyncComputedVar

_BUTTON_KINDS: dict[str, dict[str, str]] = {
    "primary": {"color_scheme": "blue"},
    "secondary": {"variant": "soft"},
    "ghost": {"variant": "ghost"},
    "danger": {"color_scheme": "red"},
    "success": {"color_scheme": "green"},
}


def action_button(
    label: str,
    *,
    kind: str = "primary",
    left_icon: str | None = None,
    right_icon: str | None = None,
    size: str = "2",
    **button_props,
) -> rx.Component:
    """One stop helper for consistent buttons across the app."""

    style = _BUTTON_KINDS.get(kind, _BUTTON_KINDS["primary"]).copy()
    style.setdefault("size", size)
    if left_icon is not None:
        return rx.button(
            rx.icon(left_icon),
            rx.text(label),
            radius="large",
            **style,
            **button_props,
        )
    if right_icon is not None:
        return rx.button(
            rx.text(label),
            rx.icon(right_icon),
            radius="large",
            **style,
            **button_props,
        )
    return rx.button(
        label,
        radius="large",
        **style,
        **button_props,
    )


def submit_button(**props) -> rx.Component:
    return action_button("Submit", left_icon="check", kind="primary", **props)


def next_button(**props) -> rx.Component:
    return action_button("Next", right_icon="arrow-right", kind="primary", **props)


def back_button(**props) -> rx.Component:
    return action_button("Back", left_icon="arrow-left", kind="secondary", **props)


def proceed_button(**props) -> rx.Component:
    return action_button("Proceed", right_icon="arrow-right", kind="primary", **props)


def cancel_button(**props) -> rx.Component:
    return action_button("Cancel", left_icon="x", kind="ghost", **props)


def save_button(**props) -> rx.Component:
    return action_button("Save", left_icon="save", kind="success", **props)


def remove_button(**props) -> rx.Component:
    return action_button("Remove", left_icon="minus", kind="danger", **props)


def delete_button(**props) -> rx.Component:
    return action_button("Delete", left_icon="trash-2", kind="danger", **props)


def dropdown_select(
    label: str,
    options: Sequence[str | Any]
    | ArrayVar[list[str]]
    | AsyncComputedVar[Sequence[str]],
    placeholder: str = "Select an option",
    value: str | rx.Var | None = None,
    on_change: EventType[Any] | None = None,
    disabled: bool = False,
    **props,
) -> rx.Component:
    """Single-select dropdown backed by Radix Select."""
    # Setting appropriate defaults
    position = props.pop("position", "item-aligned")
    size = props.pop("size", "2")
    variant = props.pop("variant", "soft")
    radius = props.pop("radius", "large")

    return rx.select(
        label=label,
        items=options,
        value=value,
        placeholder=placeholder,
        on_change=on_change,
        disabled=disabled,
        position=position,
        size=size,
        variant=variant,
        radius=radius,
        **props,
    )


def radio_select(
    options: Sequence,
    value: str | rx.Var | None = None,
    on_change: EventType[Any] | None = None,
    direction: Literal["row", "column"] = "row",
    **props,
) -> rx.Component:
    """Radio button list with optional horizontal or vertical layout."""
    # Setting appropriate defaults
    spacing = props.pop("spacing", "3")
    size = props.pop("size", "2")
    variant = props.pop("variant", "soft")

    return rx.radio_group(
        items=options,
        value=value,
        on_change=on_change,
        direction=direction,
        spacing=spacing,
        size=size,
        variant=variant,
        **props,
    )


def multi_select_dropdown(
    label: str | None,
    options: list | ArrayVar[list[str]],
    value: list[str] | rx.Var | None = None,
    on_change: EventType[Any] | Callable | None = None,
    **props,
):
    """Multi-select dropdown using Reflex Enterprise MultiSelect component."""
    return rxe.mantine.multi_select(
        label=label,
        data=options,
        value=value,
        on_change=on_change,
        searchable=True,
        clearable=True,
        nothing_found="No options found",
        clear_search_on_change=True,
        hide_picked_options=True,
        **props,
    )


def checkbox_input(
    label: str | None = None,
    on_change: EventType[Any] | None = None,
    **props,
) -> rx.Component:
    """Simple checkbox group useful as a multi-select list."""
    # Setting appropriate defaults
    spacing = props.pop("spacing", "3")
    size = props.pop("size", "2")
    variant = props.pop("variant", "soft")
    high_contrast = props.pop("high_contrast", True)
    checked = props.pop("value", None)

    # to accept boolean value for checked state
    if checked is not None and "checked" not in props:
        props["checked"] = checked

    return rx.checkbox(
        text=label,
        spacing=spacing,
        size=size,
        variant=variant,
        high_contrast=high_contrast,
        on_change=on_change,
        **props,
    )


def text_input(
    placeholder: str = "",
    on_change: EventType[Any] | None = None,
    type: str = "text",
    **props,
) -> rx.Component:
    """Basic text input with sensible defaults."""
    # Setting appropriate defaults
    radius = props.pop("radius", "medium")
    size = props.pop("size", "2")
    variant = props.pop("variant", "surface")

    return rx.input(
        placeholder=placeholder,
        on_change=on_change,
        type=type,
        radius=radius,
        size=size,
        variant=variant,
        **props,
    )


def text_area(
    value: str | rx.Var | None = None,
    on_change: EventType[Any] | None = None,
    placeholder: str = "",
    rows: int = 4,
    width: str = "100%",
    **props,
) -> rx.Component:
    """Textarea with consistent sizing."""

    return rx.text_area(
        value=value,
        on_change=on_change,
        placeholder=placeholder,
        height=f"{rows * 1.5}rem",
        width=width,
        **props,
    )


def number_input(
    *,
    value: float | int | rx.Var | None = None,
    on_change: EventType[Any] | None = None,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
    step: float | int | None = None,
    width: str = "100%",
) -> rx.Component:
    """Numeric input wrapper so we avoid retyping common props."""

    if step is None:
        return rx.input(
            value=value,
            on_change=on_change,
            type="number",
            min=min_value,
            max=max_value,
            step=step,
            width=width,
        )
    can_compute = isinstance(value, (int, float)) and isinstance(step, (int, float))
    dec_disabled = value is None
    inc_disabled = value is None
    if can_compute:
        dec_disabled = False if min_value is None else (value - step) < min_value
        inc_disabled = False if max_value is None else (value + step) > max_value

    def _step_click(delta: float | int):
        if on_change is None or value is None:
            return None
        return lambda: on_change(value + delta)

    return rx.hstack(
        rx.input(
            value=value,
            on_change=on_change,
            type="number",
            min=min_value,
            max=max_value,
            step=step,
            width="100%",
            flex="1",
        ),
        rx.button(
            "-",
            on_click=_step_click(-step),
            size="1",
            variant="soft",
            is_disabled=dec_disabled,
        ),
        rx.button(
            "+",
            on_click=_step_click(step),
            size="1",
            variant="soft",
            is_disabled=inc_disabled,
        ),
        align="center",
        spacing="2",
        width=width,
    )


def switch_input(
    checked: bool | rx.Var | None = None,
    on_change: EventType[Any] | None = None,
    label: str | None = None,
    size: str = "2",
    **props,
) -> rx.Component:
    """Boolean switch often used for feature toggles."""
    # Setting appropriate defaults
    radius = props.pop("radius", "full")
    variant = props.pop("variant", "surface")

    control = rx.switch(
        checked=checked,
        on_checked_change=on_change,
        size=size,
        radius=radius,
        variant=variant,
        **props,
    )
    if label is None:
        return control

    return rx.hstack(rx.text(label), control, align="center", spacing="2")


def slider_input(
    default_value: int | float | rx.Var | None = None,
    orientation: Literal["horizontal", "vertical"] = "horizontal",
    on_change: EventType[Any] | None = None,
    min_value: float = 0,
    max_value: float = 100,
    step: float = 1,
    **props,
) -> rx.Component:
    """Slider input for selecting a value within a range."""
    # Setting appropriate defaults
    size = props.pop("size", "1")
    variant = props.pop("variant", "soft")

    return rx.slider(
        default_value=default_value,
        on_change=on_change,
        min=min_value,
        max=max_value,
        step=step,
        size=size,
        orientation=orientation,
        variant=variant,
        **props,
    )
