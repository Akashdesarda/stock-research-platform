import reflex as rx
import reflex_enterprise as rxe

from webapp.components.inputs import (
    cancel_button,
    dropdown_select,
    multi_select_dropdown,
    reset_button,
    submit_button,
    text_area,
    text_input,
)
from webapp.components.layout import (
    bordered_container,
    callout_message,
    empty_state_card,
    form_field,
    responsive_grid,
    subsection_header,
)
from webapp.state.playground._strategy import ApplyStrategyState
from webapp.types import RunState


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
                row["strategy_id"], row["name"], value
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


def _strategy_param_group(strategy: rx.Var[dict[str, str]]) -> rx.Component:
    """One selected strategy's parameter form, boxed and driven by its own param rows."""
    return bordered_container(
        subsection_header(strategy["name"], size="2"),
        responsive_grid(
            rx.foreach(
                ApplyStrategyState.param_rows_by_strategy[strategy["id"]],
                _param_field,
            ),
            columns=[1, 2, 2],
            spacing="5",
        ),
        width="100%",
        max_width="100%",
        padding="20px",
    )


def _parameters_section() -> rx.Component:
    return rx.vstack(
        subsection_header("Edit Strategy Parameters", size="3"),
        rx.cond(
            ApplyStrategyState.params_error != "",
            callout_message(
                ApplyStrategyState.params_error, tone="error", size="1"
            ),
        ),
        rx.cond(
            ApplyStrategyState.has_params,
            rx.vstack(
                responsive_grid(
                    rx.foreach(
                        ApplyStrategyState.selected_strategies_info,
                        _strategy_param_group,
                    ),
                    columns=[1, 1, 2],
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
                spacing="5",
                width="100%",
                align_items="stretch",
            ),
            empty_state_card(
                "Select at least one strategy to configure its parameters"
            ),
        ),
        spacing="4",
        width="100%",
        align_items="stretch",
    )


def _submit_workflow() -> rx.Component:
    """Submit / reset controls, with an in-flight spinner and cancel."""
    is_applying = ApplyStrategyState.apply_state == RunState.generating.value

    return rx.hstack(
        submit_button(
            on_click=ApplyStrategyState.apply_strategy,
            disabled=~ApplyStrategyState.can_apply | is_applying,
        ),
        reset_button(
            on_click=ApplyStrategyState.reset_params,
            disabled=~ApplyStrategyState.has_params | is_applying,
        ),
        rx.cond(
            is_applying,
            rx.hstack(
                rx.spinner(size="3"),
                rx.text(
                    "Applying Strategy...",
                    size="3",
                    color=rx.color("blue", 11),
                ),
                cancel_button(on_click=ApplyStrategyState.cancel_applying),
                spacing="3",
                align="center",
            ),
        ),
        spacing="4",
        align="center",
        width="100%",
    )


def _results_view() -> rx.Component:
    """Preview of the data returned by applying the strategy."""
    return rx.cond(
        ApplyStrategyState.apply_data_ready,
        rx.vstack(
            rx.spacer(size="3", width="100%"),
            subsection_header(
                "Preview of the applied strategy output", size="3"
            ),
            rxe.ag_grid(
                id="apply_strategy_preview_grid",
                row_data=ApplyStrategyState.data,
                column_defs=ApplyStrategyState.columns_def,
                pagination=True,
                pagination_page_size=10,
                pagination_page_size_selector=[10, 40, 100],
                width="100%",
                height="500px",
            ),
            width="100%",
            spacing="4",
        ),
    )


def _or_separator() -> rx.Component:
    return rx.hstack(
        rx.separator(style={"flex": 1}),
        rx.text("OR", size="4", weight="bold", color="gray"),
        rx.separator(style={"flex": 1}),
        width="100%",
        align="center",
        padding_y="2",
    )


def _ai_submit_workflow() -> rx.Component:
    """Submit control for the AI strategy-application workflow."""
    is_generating = ApplyStrategyState.run_state == RunState.generating.value

    return rx.hstack(
        submit_button(
            on_click=ApplyStrategyState.submit_ai_prompt,
            disabled=(ApplyStrategyState.ai_prompt == "") | is_generating,
        ),
        rx.cond(
            is_generating,
            rx.hstack(
                rx.spinner(size="3"),
                rx.text(
                    "Applying Strategy...",
                    size="3",
                    color=rx.color("blue", 11),
                ),
                cancel_button(on_click=ApplyStrategyState.cancel_ai_workflow),
                spacing="3",
                align="center",
            ),
            rx.fragment(),
        ),
        spacing="4",
        align="center",
        width="100%",
    )


def _ai_explanations() -> rx.Component:
    """Show LLM rationale for the dataset and strategies it selected."""
    return rx.vstack(
        rx.cond(
            ApplyStrategyState.dataset_explanation != "",
            callout_message(
                ApplyStrategyState.dataset_explanation,
                tone="info",
                size="1",
            ),
        ),
        rx.cond(
            ApplyStrategyState.strategies_explanation != "",
            callout_message(
                ApplyStrategyState.strategies_explanation,
                tone="info",
                size="1",
            ),
        ),
        spacing="3",
        width="100%",
    )


def _ai_prompt_section() -> rx.Component:
    return rx.vstack(
        subsection_header("Describe your analysis requirement", size="3"),
        form_field(
            label="Enter your prompt",
            control=text_area(
                value=ApplyStrategyState.ai_prompt,
                on_change=ApplyStrategyState.set_ai_prompt,
                placeholder=(
                    "Example: Apply RSI strategy on my NSE tech dataset "
                    "and show stocks with RSI below 30"
                ),
                rows=4,
            ),
            help_text=(
                "Describe the dataset, strategy, and parameters you want. "
                "StockSense will fill the form below; review and click Submit to apply."
            ),
        ),
        rx.cond(
            ApplyStrategyState.workflow_error != "",
            callout_message(
                ApplyStrategyState.workflow_error, tone="error", size="1"
            ),
        ),
        _ai_submit_workflow(),
        spacing="4",
        width="100%",
    )


def _manual_selection_section() -> rx.Component:
    return rx.vstack(
        subsection_header("Dataset & Strategy selection", size="3"),
        _ai_explanations(),
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
                control=multi_select_dropdown(
                    label=None,
                    options=ApplyStrategyState.available_strategies_dropdown,
                    value=ApplyStrategyState.select_strategy_dropdown,
                    on_change=ApplyStrategyState.set_select_strategy_ids,
                    placeholder="Select one or more strategies",
                    width="100%",
                ),
            ),
            columns=[2, 2, 2],
            spacing="5",
        ),
        _parameters_section(),
        spacing="4",
        width="100%",
    )


def apply_strategy_panel() -> rx.Component:
    return rx.vstack(
        _ai_prompt_section(),
        _or_separator(),
        _manual_selection_section(),
        rx.cond(
            ApplyStrategyState.apply_error != "",
            callout_message(ApplyStrategyState.apply_error, tone="error"),
        ),
        _submit_workflow(),
        _results_view(),
        spacing="8",
        width="100%",
    )
