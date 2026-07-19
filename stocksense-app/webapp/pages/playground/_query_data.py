import reflex as rx
import reflex_enterprise as rxe
from stocksense.types import DataInterval, DataPeriod

from webapp.components.inputs import (
    cancel_button,
    checkbox_input,
    date_range_picker,
    dropdown_select,
    submit_button,
    tags_input,
    text_area,
)
from webapp.components.layout import (
    bordered_container,
    dialog_actions,
    dialog_form,
    form_field,
    refined_markdown,
    section_header,
)
from webapp.pages.shared_components import ticker_selector, workflow_steps
from webapp.state.playground import DataState
from webapp.types import RunState


def _register_dataset_dialog() -> rx.Component:
    """Dialog (Modal) for registering a new dataset."""
    return dialog_form(
        form_field(
            label="Dataset Name",
            control=text_area(
                placeholder="Enter name OR leave blank for AI-generated name",
                value=DataState.dataset_name,
                on_change=DataState.set_dataset_name,
                rows=1,
            ),
        ),
        form_field(
            label="Description",
            control=text_area(
                placeholder="Enter description OR leave blank for AI-generated description",
                value=DataState.dataset_description,
                on_change=DataState.set_dataset_description,
                rows=3,
            ),
        ),
        form_field(
            label="Tags",
            control=tags_input(
                label=None,
                value=DataState.dataset_tags,
                on_change=DataState.set_dataset_tags,
            ),
            help_text="Press Enter to add tags for categorization.",
        ),
        title="Register Dataset",
        description="Register this dataset for regular future use.",
        actions=dialog_actions(
            on_submit=DataState.register_dataset,
            on_cancel=DataState.close_register_dialog,
            submit_label="Submit",
        ),
        open=DataState.register_dialog_open,
        on_open_change=DataState.close_register_dialog,
    )


def _results_view() -> rx.Component:
    """Shared view for displaying fetched data results."""
    return rx.cond(
        DataState.fetch_data_ready,
        rx.vstack(
            rx.separator(size="4", width="100%"),
            section_header(
                rx.cond(
                    DataState.preview_enabled,
                    "Data Preview",
                    "Data Fetched Successfully",
                ),
                rx.cond(
                    DataState.preview_enabled,
                    "Preview the fetched data before registering.",
                    "You can now register this dataset.",
                ),
            ),
            rx.cond(
                DataState.preview_enabled,
                rxe.ag_grid(
                    id="data_preview_grid",
                    row_data=DataState.data,
                    column_defs=DataState.columns_def,
                    pagination=True,
                    pagination_page_size=10,
                    pagination_page_size_selector=[10, 40, 100],
                    width="100%",
                    height="500px",
                ),
                rx.fragment(),
            ),
            rx.hstack(
                rx.button(
                    rx.icon("save", size=16),
                    "Register Dataset",
                    size="3",
                    on_click=DataState.open_register_dialog,
                ),
                rx.spacer(),
                width="100%",
            ),
            _register_dataset_dialog(),
            width="100%",
            spacing="4",
        ),
        rx.fragment(),
    )


def _submit_workflow(on_click=None, disabled=None) -> rx.Component:
    """Controls for submitting data fetch request or cancelling."""
    if on_click is None:
        on_click = DataState.fetch_data
    if disabled is None:
        disabled = DataState.fetch_state == RunState.generating.value

    return rx.hstack(
        submit_button(
            on_click=on_click,
            disabled=disabled,
        ),
        rx.cond(
            DataState.fetch_state == RunState.generating.value,
            rx.hstack(
                rx.spinner(size="3"),
                rx.text(
                    "Fetching Data...",
                    size="3",
                    color=rx.color("blue", 11),
                ),
                cancel_button(on_click=DataState.cancel_fetching),
                spacing="3",
                align="center",
            ),
            rx.fragment(),
        ),
        spacing="4",
        align="center",
        width="100%",
    )


def manual_panel() -> rx.Component:
    return bordered_container(
        rx.vstack(
            # exch, tkr selection --> query params --> OR --> sql query --> callout --> submit
            # SECTION - Exchange and Ticker
            ticker_selector(DataState),
            rx.separator(size="4", width="100%"),
            # SECTION - Time Range
            rx.vstack(  # interval --> period/date range --> callout with conditions
                rx.spacer(),
                rx.text(
                    "Time Range Selection",
                    size="2",
                    weight="medium",
                    color_scheme="gray",
                ),
                rx.hstack(  # interval + separator
                    form_field(
                        label="Data Interval",
                        control=dropdown_select(
                            label="Data Interval",
                            options=[i.value for i in DataInterval],
                            value=DataState.interval,
                            on_change=DataState.set_interval,
                            width="100%",
                        ),
                        help_text="Time interval between historical data points",
                    ),
                    rx.spacer(),
                    width="100%",
                    spacing="4",
                ),
                rx.hstack(  # OR separator + period/date range
                    form_field(
                        label="Data Period",
                        control=dropdown_select(
                            label="Data Period",
                            options=[i.value for i in DataPeriod],
                            value=DataState.period,
                            on_change=DataState.set_period,
                            width="100%",
                        ),
                        help_text="Day period between historical data points",
                    ),
                    rx.center(  # OR separator
                        rx.vstack(
                            rx.text("OR", size="1", weight="bold", color="gray"),
                            rx.separator(
                                orientation="vertical",
                                size="4",
                                height="40px",
                            ),
                            align="center",
                            justify="end",
                            height="100%",
                            padding_top="28px",
                        ),
                        width="10%",
                    ),
                    # date range picker
                    date_range_picker(
                        on_change_start=DataState.set_date_start,
                        value_start=DataState.date_start,
                        on_change_end=DataState.set_date_end,
                        value_end=DataState.date_end,
                        help_text="If set, 'Data Period' selection is ignored.",
                        width="100%",
                    ),
                    width="100%",
                    spacing="4",
                    align="start",
                ),
                rx.cond(  # callout for period + date range both set
                    (DataState.period != "")
                    & (DataState.date_start != "")
                    & (DataState.date_end != ""),
                    rx.callout(
                        "Date Range selection will be prioritized over the Data Period.",
                        icon="info",
                        color_scheme="yellow",
                        width="100%",
                    ),
                ),
                width="100%",
                spacing="4",
            ),
            rx.spacer(size="4"),
            rx.hstack(  # OR separator
                rx.separator(style={"flex": 1}),
                rx.text("OR", size="4", weight="bold", color="gray"),
                rx.separator(style={"flex": 1}),
                width="100%",
                align="center",
                padding_y="2",
            ),
            form_field(  # sql query input
                label="Use your own SQL query",
                control=text_area(
                    value=DataState.sql_query,
                    on_change=DataState.set_sql_query,
                    placeholder="Write your SQL query",
                    rows=4,
                ),
            ),
            rx.cond(  # callout for sql query + other params both set
                (DataState.sql_query != "") & (DataState.selected_ticker != []),
                rx.callout(
                    "SQL Query will be prioritized over other selection parameters.",
                    icon="info",
                    color_scheme="yellow",
                    width="100%",
                ),
            ),
            rx.spacer(),
            checkbox_input(
                label="Enable data preview",
                value=DataState.preview_enabled,
                on_change=DataState.set_preview_enabled,
            ),
            rx.cond(
                DataState.agent_error != "",
                rx.callout(
                    DataState.agent_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
                rx.fragment(),
            ),
            _submit_workflow(
                disabled=(DataState.selected_exchange == "")
                | (DataState.fetch_state == RunState.generating.value)
            ),
            width="100%",
            spacing="4",
        ),
        width="100%",
    )


def ai_panel() -> rx.Component:
    return bordered_container(
        rx.vstack(
            ticker_selector(DataState),
            rx.separator(size="4", width="100%"),
            rx.vstack(
                rx.text("AI-Powered Data Query", size="3", weight="medium"),
                form_field(
                    label="Enter your data query prompt",
                    control=text_area(
                        value=DataState.ai_prompt,
                        on_change=DataState.set_ai_prompt,
                        placeholder="Ask a question about the data you want...",
                        rows=3,
                    ),
                ),
                checkbox_input(
                    label="Use Cache (if available)",
                    value=DataState.ai_use_cache,
                    on_change=DataState.set_ai_use_cache,
                ),
                rx.hstack(
                    submit_button(
                        on_click=DataState.generate_text_to_sql,
                        disabled=(DataState.run_state == RunState.generating.value)
                        | (DataState.ai_prompt == "")
                        | (DataState.selected_exchange == ""),
                    ),
                    rx.cond(
                        DataState.run_state == RunState.generating.value,
                        cancel_button(on_click=DataState.cancel_agent_run),
                        rx.fragment(),
                    ),
                    spacing="4",
                    align="center",
                    width="100%",
                ),
                rx.cond(
                    (DataState.run_state == RunState.generating.value)
                    | (DataState.agent_status_message != ""),
                    workflow_steps(DataState),
                    rx.fragment(),
                ),
                rx.cond(
                    DataState.agent_error != "",
                    rx.callout(
                        DataState.agent_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    DataState.ai_generated_sql != "",
                    rx.vstack(
                        rx.text("Generated SQL", size="2", weight="medium"),
                        refined_markdown("```sql\n" + DataState.ai_generated_sql + "\n```"),
                        form_field(
                            label="Edit SQL before running",
                            control=text_area(
                                value=DataState.ai_sql_query,
                                on_change=DataState.set_ai_sql_query,
                                placeholder="Edit the SQL query...",
                                rows=15,
                            ),
                        ),
                        checkbox_input(
                            label="Enable data preview",
                            value=DataState.preview_enabled,
                            on_change=DataState.set_preview_enabled,
                        ),
                        _submit_workflow(
                            on_click=[
                                DataState.submit_ai,
                                DataState.fetch_data,
                            ],
                            disabled=(DataState.selected_exchange == "")
                            | (DataState.fetch_state == RunState.generating.value)
                            | (DataState.ai_sql_query == ""),
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                spacing="3",
                width="100%",
            ),
            width="100%",
            spacing="4",
        ),
        width="100%",
    )
