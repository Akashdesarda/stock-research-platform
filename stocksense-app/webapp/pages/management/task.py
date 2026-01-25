import reflex as rx

from webapp.components.inputs import (
    checkbox_input,
    dropdown_select,
    multi_select_dropdown,
    radio_select,
    submit_button,
)
from webapp.components.layout import (
    form_field,
    page_layout_with_sidebar,
    section_header,
)
from webapp.components.sidebar import nav_sidebar
from webapp.state.management import TaskState


def _manual_fields() -> rx.Component:
    return rx.vstack(
        rx.cond(
            TaskState.task_mode == "manual",
            form_field(
                label="Select Tickers",
                control=multi_select_dropdown(
                    label=None,
                    options=TaskState.ticker_dropdown_list,
                    value=TaskState.selected_ticker_dropdowns,
                    on_change=TaskState.set_ticker_dropdowns,
                    placeholder="Select one or more tickers",
                ),
                help_text="Select one or more tickers to update data for.",
            ),
            rx.fragment(),
        ),
        rx.cond(
            TaskState.task_mode == "manual",
            rx.hstack(
                form_field(
                    label="Start Date",
                    control=rx.input(
                        type="date",
                        value=TaskState.start_date,
                        on_change=TaskState.set_start_date,
                        width="100%",
                        radius="large",
                    ),
                ),
                form_field(
                    label="End Date",
                    control=rx.input(
                        type="date",
                        value=TaskState.end_date,
                        on_change=TaskState.set_end_date,
                        width="100%",
                        radius="large",
                    ),
                ),
                width="100%",
                spacing="4",
                wrap="wrap",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="4",
    )


def _auto_mode_notice() -> rx.Component:
    return rx.callout(
        "Auto Mode Selected - Tickers and date range will be determined automatically.",
        icon="info",
        color_scheme="blue",
        width="100%",
    )


def task() -> rx.Component:
    sidebar = nav_sidebar(default_open_group="Management")

    tasks_tab_list = rx.tabs.list(
        rx.tabs.trigger(
            rx.hstack(rx.icon("database", size=20), rx.text("Update Data", size="3")),
            value="update_data",
        ),
        rx.tabs.trigger(
            rx.hstack(
                rx.icon("smile_plus", size=20), rx.text("Optimize Table", size="3")
            ),
            value="optimize_table",
        ),
    )

    update_data_tab = rx.tabs.content(
        rx.vstack(
            rx.hstack(
                form_field(
                    label="Select Exchange",
                    control=dropdown_select(
                        label="",
                        options=TaskState.exchange_dropdown_list,
                        value=TaskState.selected_exchange_dropdown,
                        on_change=TaskState.set_exchange_dropdown,
                        placeholder="Select the exchange",
                    ),
                ),
                form_field(
                    label="Task Mode",
                    control=radio_select(
                        options=["auto", "manual"],
                        value=TaskState.task_mode,
                        on_change=TaskState.set_task_mode,
                        direction="row",
                    ),
                    help_text=(
                        "`auto` determines required tickers and date range; "
                        "`manual` lets you select tickers and dates."
                    ),
                ),
                form_field(
                    label="Download Mode",
                    control=radio_select(
                        options=["incremental", "full"],
                        value=TaskState.download_mode,
                        on_change=TaskState.set_download_mode,
                        direction="row",
                    ),
                    help_text=(
                        "`incremental` fetches only new data from the last update. It's faster & cheaper; "
                        "`full` downloads complete historical data. Use for first-time setup or full refresh."
                    ),
                ),
                width="100%",
                spacing="4",
                align="start",
                wrap="wrap",
            ),
            rx.cond(
                TaskState.task_mode == "manual",
                _manual_fields(),
                _auto_mode_notice(),
            ),
            rx.hstack(
                submit_button(
                    on_click=TaskState.submit_task,
                    disabled=TaskState.is_submitting,
                ),
                rx.cond(
                    TaskState.is_submitting,
                    rx.hstack(
                        rx.spinner(size="3"),
                        rx.text(
                            "Running...",
                            size="3",
                            color=rx.color("blue", 11),
                        ),
                        spacing="3",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                width="100%",
                spacing="3",
                align="center",
            ),
            rx.cond(
                TaskState.submit_success != "",
                rx.callout(
                    TaskState.submit_success,
                    icon="circle_check",
                    color_scheme="green",
                    width="100%",
                ),
                rx.fragment(),
            ),
            rx.cond(
                TaskState.submit_error != "",
                rx.callout(
                    TaskState.submit_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
                rx.fragment(),
            ),
            width="100%",
            spacing="4",
        ),
        value="update_data",
        width="100%",
    )

    optimize_table_tab = rx.tabs.content(
        rx.vstack(
            form_field(
                label="Select Exchange",
                control=dropdown_select(
                    label="",
                    options=TaskState.exchange_dropdown_list,
                    value=TaskState.selected_exchange_dropdown,
                    on_change=TaskState.set_exchange_dropdown,
                    placeholder="Select the exchange",
                ),
            ),
            rx.hstack(
                checkbox_input(
                    "compact", value=TaskState.compact, on_change=TaskState.set_compact
                ),
                checkbox_input(
                    "vacuum", value=TaskState.vacuum, on_change=TaskState.set_vacuum
                ),
                spacing="4",
                align="start",
            ),
        ),
        value="optimize_table",
    )

    tasks_tabs = rx.tabs.root(
        tasks_tab_list,
        update_data_tab,
        optimize_table_tab,
        default_value="update_data",
        width="100%",
        justify="between",
    )

    return page_layout_with_sidebar(
        rx.vstack(
            section_header(
                "Tasks",
                "Run variety of workflows for StockSense.",
            ),
            # bordered_container(
            tasks_tabs,
            #     width="100%",
            #     max_width="900px",
            #     align="left",
            # ),
            width="100%",
            spacing="5",
        ),
        sidebar=sidebar,
    )
