import reflex as rx
import reflex_enterprise as rxe
from stocksense.types import DataInterval, DataPeriod

from webapp.components.inputs import (
    dropdown_select,
    refresh_button,
    tags_input,
    text_area,
    text_input,
)
from webapp.components.layout import (
    bordered_container,
    dialog_actions,
    dialog_form,
    form_field,
)
from webapp.pages.shared_components import ticker_selector
from webapp.state.playground import (
    DATASET_COLUMN_DEFS,
    DATASET_DETAIL_PARAMS,
    RegisteredDatasetState,
)


def _edit_dataset_dialog() -> rx.Component:
    """Dialog for editing a selected dataset."""
    return dialog_form(
        form_field(
            label="Dataset Name",
            control=text_input(
                placeholder="Enter dataset name",
                value=RegisteredDatasetState.edit_dataset_name,
                on_change=RegisteredDatasetState.set_edit_dataset_name,
                width="100%",
            ),
        ),
        form_field(
            label="Description",
            control=text_area(
                placeholder="Enter description",
                value=RegisteredDatasetState.edit_dataset_description,
                on_change=RegisteredDatasetState.set_edit_dataset_description,
                rows=3,
            ),
        ),
        form_field(
            label="Tags",
            control=tags_input(
                label=None,
                value=RegisteredDatasetState.edit_dataset_tags,
                on_change=RegisteredDatasetState.set_edit_dataset_tags,
                width="100%",
            ),
            help_text="Press Enter to add tags for categorization.",
        ),
        rx.separator(size="4", width="100%"),
        ticker_selector(RegisteredDatasetState),
        rx.separator(size="4", width="100%"),
        rx.vstack(
            rx.text(
                "Time Range Selection",
                size="2",
                weight="medium",
                color_scheme="gray",
            ),
            rx.hstack(
                form_field(
                    label="Data Interval",
                    control=dropdown_select(
                        label="Data Interval",
                        options=[i.value for i in DataInterval],
                        value=RegisteredDatasetState.interval,
                        on_change=RegisteredDatasetState.set_interval,
                        width="100%",
                    ),
                    help_text="Time interval between historical data points",
                ),
                rx.spacer(),
                width="100%",
                spacing="4",
            ),
            rx.hstack(
                form_field(
                    label="Data Period",
                    control=dropdown_select(
                        label="Data Period",
                        options=[i.value for i in DataPeriod],
                        value=RegisteredDatasetState.period,
                        on_change=RegisteredDatasetState.set_period,
                        width="100%",
                    ),
                    help_text="Used when no explicit date range is provided.",
                ),
                form_field(
                    label="Start Date",
                    control=rx.input(
                        type="date",
                        value=RegisteredDatasetState.date_start,
                        on_change=RegisteredDatasetState.set_date_start,
                        width="100%",
                    ),
                ),
                form_field(
                    label="End Date",
                    control=rx.input(
                        type="date",
                        value=RegisteredDatasetState.date_end,
                        on_change=RegisteredDatasetState.set_date_end,
                        width="100%",
                    ),
                ),
                width="100%",
                spacing="4",
            ),
            form_field(
                label="SQL Query",
                control=text_area(
                    value=RegisteredDatasetState.sql_query,
                    on_change=RegisteredDatasetState.set_sql_query,
                    placeholder="Optional SQL query. If provided, it takes precedence over ticker/date selections.",
                    rows=4,
                ),
                help_text="When SQL is provided, it overrides ticker and time-range based logical plan fields.",
            ),
            width="100%",
            spacing="4",
        ),
        title="Edit Dataset",
        description="Update the selected dataset metadata and logical plan.",
        actions=dialog_actions(
            on_submit=RegisteredDatasetState.update_dataset,
            on_cancel=RegisteredDatasetState.close_edit_dialog,
            submit_label="Submit",
        ),
        max_width="760px",
        open=RegisteredDatasetState.edit_dialog_open,
        on_open_change=RegisteredDatasetState.close_edit_dialog,
    )


def registered_data_panel() -> rx.Component:
    return bordered_container(
        rx.vstack(
            rxe.ag_grid(
                id="registered-datasets-grid",
                row_data=RegisteredDatasetState.datasets,
                column_defs=DATASET_COLUMN_DEFS,
                master_detail=True,
                detail_cell_renderer_params=DATASET_DETAIL_PARAMS,
                row_selection="single",
                on_selection_changed=RegisteredDatasetState.set_selected_dataset_ids,
                enable_cell_text_selection=True,
                ensure_dom_order=True,
                dom_layout="autoHeight",
                width="100%",
            ),
            bordered_container(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Edit Dataset", size="4"),
                        rx.spacer(),
                        refresh_button(
                            on_click=RegisteredDatasetState.force_refresh,
                            size="2",
                        ),
                        width="100%",
                        align_items="center",
                    ),
                    rx.text(
                        "Select a dataset row from the grid, or enter a dataset ID manually, then open it in the edit dialog.",
                        color=rx.color("gray", 11),
                        size="2",
                    ),
                    rx.hstack(
                        form_field(
                            label="Dataset ID",
                            control=text_input(
                                placeholder="Enter dataset id",
                                value=RegisteredDatasetState.selected_dataset_id,
                                on_change=RegisteredDatasetState.set_selected_dataset_id,
                                width="100%",
                            ),
                        ),
                        rx.button(
                            rx.icon("pencil", size=16),
                            "Edit Selected",
                            on_click=RegisteredDatasetState.edit_selected_dataset,
                            loading=RegisteredDatasetState.edit_is_loading,
                            size="2",
                        ),
                        width="100%",
                        align_items="end",
                        spacing="4",
                    ),
                    width="100%",
                    spacing="4",
                ),
                width="100%",
            ),
            _edit_dataset_dialog(),
            width="100%",
            spacing="6",
        )
    )
