import reflex as rx

from webapp.components.inputs import (
    action_button,
    multi_select_dropdown,
    number_input,
    save_button,
)
from webapp.components.layout import (
    bordered_container,
    form_field,
    section_header,
)
from webapp.state.management import ConfigurationState


def new_configuration() -> rx.Component:
    # SECTION - Configuration Tabs
    config_tabs_list = rx.tabs.list(
        rx.tabs.trigger("🏗️ Common", value="common"),
        rx.tabs.trigger("🛢️ StockDB", value="stockdb"),
        rx.tabs.trigger("💻 App", value="app"),
    )
    common_tab = rx.tabs.content(
        rx.vstack(
            rx.spacer(spacing="3"),
            form_field(
                label="Common Base URL",
                control=rx.input(
                    value=ConfigurationState.common_base_url,
                    on_change=ConfigurationState.update_base_url,
                ),
                help_text="Base URL for the APIs. Only change if you know what you are doing.",
            ),
            form_field(
                label="Available LLM Providers",
                control=multi_select_dropdown(
                    label=None,
                    options=ConfigurationState.common_available_llm_providers,
                    value=ConfigurationState.llm_providers_to_use,
                    placeholder="Select LLM Providers",
                ),
                help_text="Select the LLM providers that you want to enable.",
            ),
            form_field(
                label="GROQ API Key",
                control=rx.input(
                    on_change=ConfigurationState.update_groq_api_key,
                    type="password",
                    width="100%",
                    radius="large",
                ),
                help_text="API key for GROQ service.",
            ),
            form_field(
                label="OPENAI API Key",
                control=rx.input(
                    on_change=ConfigurationState.update_openai_api_key,
                    type="password",
                    width="100%",
                    radius="large",
                ),
                help_text="API key for OpenAI ChatGPT service.",
            ),
            form_field(
                label="ANTHROPIC API Key",
                control=rx.input(
                    on_change=ConfigurationState.update_anthropic_api_key,
                    type="password",
                    width="100%",
                    radius="large",
                ),
                help_text="API key for Anthropic Claude service.",
            ),
            form_field(
                label="GOOGLE API Key",
                control=rx.input(
                    type="password",
                    width="100%",
                    radius="large",
                    on_change=ConfigurationState.update_google_api_key,
                ),
                help_text="API key for Google Gemini service.",
            ),
            form_field(
                label="MLflow Port",
                control=number_input(
                    on_change=ConfigurationState.update_mlflow_port,
                    width="100%",
                    value=ConfigurationState.common_mlflow_port,
                ),
                help_text="Port number for MLflow tracking server.",
            ),
        ),
        value="common",
        width="100%",
    )

    stockdb_tab = rx.tabs.content(
        rx.vstack(
            rx.spacer(spacing="3"),
            form_field(
                label="StockDB API Port",
                control=number_input(
                    value=ConfigurationState.stockdb_port,
                    on_change=ConfigurationState.update_stockdb_port,
                    width="100%",
                ),
                help_text="Port for StockDB API server. Only change if you know what you are doing.",
            ),
            form_field(
                label="Download Batch Size",
                control=number_input(
                    value=ConfigurationState.stockdb_download_batch_size,
                    on_change=ConfigurationState.update_stockdb_download_batch_size,
                    width="100%",
                    min_value=50,
                    max_value=200,
                    step=10,
                ),
                help_text="Number of records to download in a single batch when downloading data. This is directly related to your available RAM.",
            ),
        ),
        value="stockdb",
        width="100%",
    )

    app_tab = rx.tabs.content(
        rx.vstack(
            rx.spacer(spacing="3"),
            form_field(
                label="App Port",
                control=number_input(
                    value=ConfigurationState.app_port,
                    on_change=ConfigurationState.update_app_port,
                    width="100%",
                ),
                help_text="Port for the Stocksense app. Only change if you know what you are doing.",
            ),
            form_field(
                label="Text to SQL Model",
                control=rx.input(
                    value=ConfigurationState.app_text_to_sql_model,
                    on_change=ConfigurationState.update_app_text_to_sql_model,
                    width="100%",
                    radius="large",
                ),
                help_text="LLM Model to use for text-to-SQL agent.",
            ),
            form_field(
                label="Company Summary Model",
                control=rx.input(
                    value=ConfigurationState.app_company_summary_model,
                    on_change=ConfigurationState.update_app_company_summary_model,
                    width="100%",
                    radius="large",
                ),
                help_text="LLM Model to use for generating company summaries agent.",
            ),
            form_field(
                label="Company Summary QA Model",
                control=rx.input(
                    value=ConfigurationState.app_company_summary_qa_model,
                    on_change=ConfigurationState.update_app_company_summary_qa_model,
                    width="100%",
                    radius="large",
                ),
                help_text="LLM Model to use for company summary question answering agent",
            ),
        ),
        value="app",
        width="100%",
    )

    config_tabs = rx.tabs.root(
        config_tabs_list,
        common_tab,
        stockdb_tab,
        app_tab,
        default_value="common",
        width="100%",
        justify="between",
    )
    return rx.vstack(
        section_header(
            "Management: Configuration",
            "Manage all configuration settings to run StockSense.",
        ),
        bordered_container(
            config_tabs,
            rx.hstack(
                save_button(on_click=ConfigurationState.update_config),
                action_button(
                    "Reload from disk",
                    kind="secondary",
                    left_icon="redo_2",
                    on_click=ConfigurationState.reload_from_disk,
                ),
                rx.spacer(),
                rx.cond(
                    ConfigurationState.last_saved != "",
                    rx.badge(
                        rx.text("Saved: ", ConfigurationState.last_saved),
                        variant="soft",
                    ),
                    rx.fragment(),
                ),
                width="100%",
                align="center",
                wrap="wrap",
            ),
            rx.cond(
                ConfigurationState.save_error != "",
                rx.callout(
                    ConfigurationState.save_error,
                    icon="triangle_alert",
                    color_scheme="red",
                    width="100%",
                ),
                rx.fragment(),
            ),
            width="80%",
            max_width="800px",
        ),
    )
