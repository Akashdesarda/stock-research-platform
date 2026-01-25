import reflex as rx

from webapp.components.inputs import (
    action_button,
    checkbox_input,
    dropdown_select,
    multi_select_dropdown,
    radio_select,
    submit_button,
    text_area,
    text_input,
)
from webapp.components.layout import (
    bordered_container,
    form_field,
    page_layout,
    section_header,
)
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


def _submit_workflow(
    on_click,
    disabled,
    submit_cond,
    success_callout_cond,
    success_msg,
    error_callout_cond,
    error_msg,
):
    h_button_stack = (
        rx.hstack(
            submit_button(
                on_click=on_click,
                disabled=disabled,
            ),
            rx.cond(
                submit_cond,
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
    )
    success_callout = (
        rx.cond(
            success_callout_cond != "",
            rx.callout(
                success_msg,
                icon="circle_check",
                color_scheme="green",
                width="100%",
            ),
            rx.fragment(),
        ),
    )
    error_callout = rx.cond(
        error_callout_cond != "",
        rx.callout(
            error_msg,
            icon="triangle_alert",
            color_scheme="red",
            width="100%",
        ),
        rx.fragment(),
    )
    return h_button_stack, success_callout, error_callout


def task() -> rx.Component:

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
        rx.tabs.trigger(
            rx.hstack(
                rx.icon("search_code", size=20), rx.text("Prompt Search", size="3")
            ),
            value="prompt_search",
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
            *_submit_workflow(
                on_click=TaskState.submit_update_data_task,
                disabled=TaskState.update_is_submitting,
                submit_cond=TaskState.update_is_submitting,
                success_callout_cond=TaskState.update_submit_success,
                success_msg=TaskState.update_submit_success,
                error_callout_cond=TaskState.update_submit_error,
                error_msg=TaskState.update_submit_error,
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
            rx.cond(
                TaskState.selected_exchange_dropdown == "",
                rx.fragment(),
                rx.hstack(
                    checkbox_input(
                        "compact",
                        value=TaskState.compact,
                        on_change=TaskState.set_compact,
                    ),
                    checkbox_input(
                        "vacuum", value=TaskState.vacuum, on_change=TaskState.set_vacuum
                    ),
                    rx.tooltip(
                        rx.icon(
                            "circle_help",
                            stroke_width=2,
                            size=18,
                            style={"verticalAlign": "middle"},
                        ),
                        content="`Compact` joins smaller data files into larger ones to improve read performance. `Vacuum` reclaims storage by removing obsolete old data files.",
                    ),
                    spacing="4",
                    align="start",
                ),
            ),
            *_submit_workflow(
                on_click=TaskState.submit_optimize_table_task,
                disabled=TaskState.optimize_is_submitting,
                submit_cond=TaskState.optimize_is_submitting,
                success_callout_cond=TaskState.optimize_submit_success,
                success_msg=TaskState.optimize_submit_success,
                error_callout_cond=TaskState.optimize_submit_error,
                error_msg=TaskState.optimize_submit_error,
            ),
            spacing="5",
        ),
        value="optimize_table",
    )

    prompt_search_tab = rx.tabs.content(
        rx.vstack(  # HStack, Prompt text area, Search button, Response area
            rx.hstack(  # Agent input, Cache Tier dropdown
                form_field(
                    label="Agent",
                    control=text_input(
                        placeholder="Enter your agent...",
                        value=TaskState.agent,
                        on_change=TaskState.set_agent,
                        size="3",
                        width="100%",
                    ),
                    help_text="Enter the name of the agent to use for the prompt search.",
                ),
                form_field(
                    label="Cache Tier",
                    control=dropdown_select(
                        label="Cache Tier",
                        options=["auto", "tier1", "tier2"],
                        value=TaskState.cache_tier,
                        on_change=TaskState.set_cache_tier,
                        placeholder="Select Cache Tier",
                        size="3",
                        width="100%",
                    ),
                    help_text="`auto` selects the optimal cache tier based on the agent and prompt; `tier1` uses high-speed cache for faster responses; `tier2` uses best-effort caching.",
                ),
                width="100%",
                spacing="4",
            ),
            form_field(
                label="Prompt",
                control=text_area(
                    placeholder="Enter your search prompt here...",
                    size="3",
                    auto_complete=True,
                    value=TaskState.prompt,
                    on_change=TaskState.set_prompt,
                    min_height="150px",
                ),
            ),
            rx.hstack(
                rx.spacer(),
                action_button(
                    "Search",
                    left_icon="search",
                    on_click=TaskState.prompt_search,
                    disabled=TaskState.prompt_search_is_submitting,
                    size="3",
                    width="150px",
                ),
                width="100%",
                padding_top="2",
            ),
            rx.cond(
                TaskState.prompt_search_error != "",
                rx.callout(
                    TaskState.prompt_search_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
                rx.fragment(),
            ),
            rx.cond(
                TaskState.prompt_thinking != "",
                bordered_container(
                    rx.heading("Thinking...", size="4"),
                    rx.markdown(
                        TaskState.prompt_thinking,
                        italic=True,
                        color=rx.color("gray", 9),
                    ),
                    width="100%",
                    align="left",
                ),
                rx.fragment(),
            ),
            rx.cond(
                TaskState.prompt_response != "",
                bordered_container(
                    rx.heading("Response:", size="4"),
                    rx.markdown(TaskState.prompt_response),
                    width="100%",
                    align="left",
                ),
                rx.fragment(),
            ),
            spacing="5",
        ),
        value="prompt_search",
    )

    tasks_tabs = rx.tabs.root(
        tasks_tab_list,
        update_data_tab,
        optimize_table_tab,
        prompt_search_tab,
        default_value="update_data",
        width="100%",
        justify="between",
    )

    return page_layout(
        rx.vstack(
            section_header(
                "Tasks",
                "Run variety of workflows for StockSense.",
            ),
            # Error callouts for data loading
            rx.cond(
                TaskState.exchanges_error != "",
                rx.callout(
                    TaskState.exchanges_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
                rx.fragment(),
            ),
            rx.cond(
                TaskState.tickers_error != "",
                rx.callout(
                    TaskState.tickers_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
                rx.fragment(),
            ),
            tasks_tabs,
            width="100%",
            spacing="5",
        ),
        on_mount=[TaskState.load_exchanges, TaskState.load_tickers],
    )
