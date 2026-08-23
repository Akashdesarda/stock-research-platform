import reflex as rx

from webapp.components.inputs import dropdown_select, text_input
from webapp.components.layout import (
    callout_message,
    empty_state_card,
    form_field,
    responsive_grid,
    subsection_header,
)
from webapp.state.playground._strategy import ApplyStrategyState


def _param_field(row: rx.Var[dict[str, str]]) -> rx.Component:
    """One editable parameter, driven entirely by its spec row."""
    has_error = row["error"] != ""

    return rx.vstack(
        rx.hstack(
            rx.code(row["name"], size="2"),
            rx.badge(row["type"], variant="soft", color_scheme="gray"),
            rx.cond(
                row["range"] != "",
                rx.text(row["range"], size="1", color=rx.color("gray", 10)),
            ),
            rx.spacer(),
            rx.cond(
                row["description"] != "",
                rx.tooltip(
                    rx.icon("circle_help", size=15, color=rx.color("gray", 10)),
                    content=row["description"],
                ),
            ),
            width="100%",
            align="center",
            spacing="2",
        ),
        text_input(
            placeholder=row["placeholder"],
            on_change=lambda value: ApplyStrategyState.set_param_value(
                row["name"], value
            ),
            type=row["input_type"],
            value=row["value"],
            step=row["step"],
            min=row["min"],
            max=row["max"],
            color_scheme=rx.cond(has_error, "red", "gray"),
            width="100%",
        ),
        rx.text(
            rx.cond(has_error, row["error"], row["hint"]),
            size="1",
            color=rx.cond(has_error, rx.color("red", 11), rx.color("gray", 10)),
        ),
        spacing="2",
        width="100%",
        align_items="stretch",
    )


def _parameters_section() -> rx.Component:
    return rx.vstack(
        subsection_header("Edit Strategy Parameters", size="3"),
        rx.cond(
            ApplyStrategyState.params_error != "",
            callout_message(ApplyStrategyState.params_error, tone="error", size="1"),
        ),
        rx.cond(
            ApplyStrategyState.has_params,
            rx.vstack(
                responsive_grid(
                    rx.foreach(ApplyStrategyState.param_rows, _param_field),
                    columns=[1, 2, 2],
                    spacing="5",
                ),
                rx.cond(
                    ApplyStrategyState.has_param_errors,
                    callout_message(
                        "Fix the highlighted parameters before applying the strategy.",
                        tone="error",
                        size="1",
                    ),
                ),
                rx.vstack(
                    rx.text("Resolved parameters", size="1", weight="medium"),
                    rx.code_block(
                        ApplyStrategyState.resolved_params_json,
                        language="json",
                        width="100%",
                        wrap_long_lines=True,
                    ),
                    spacing="2",
                    width="100%",
                    align_items="stretch",
                ),
                spacing="5",
                width="100%",
                align_items="stretch",
            ),
            empty_state_card("Select a strategy to configure its parameters"),
        ),
        spacing="4",
        width="100%",
        align_items="stretch",
    )


def apply_strategy_panel() -> rx.Component:
    return rx.vstack(
        subsection_header("Dataset & Strategy selection", size="3"),
        responsive_grid(
            form_field(
                label="Select Dataset",
                control=dropdown_select(
                    label="Select Dataset",
                    options=ApplyStrategyState.available_datasets_dropdown,
                    value=ApplyStrategyState.select_dataset_dropdown,
                    on_change=ApplyStrategyState.set_select_dataset_id,
                    width="100%",
                ),
            ),
            form_field(
                label="Select Strategy",
                control=dropdown_select(
                    label="Select Strategy",
                    options=ApplyStrategyState.available_strategies_dropdown,
                    value=ApplyStrategyState.select_strategy_dropdown,
                    on_change=ApplyStrategyState.set_select_strategy_id,
                    width="100%",
                ),
            ),
            columns=[2, 2, 2],
            spacing="5",
        ),
        _parameters_section(),
        spacing="8",
        width="100%",
    )
