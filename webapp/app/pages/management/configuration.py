import streamlit as st
from stocksense.config import get_settings

settings = get_settings()
st.title("Configuration management")
st.markdown("Manage all configuration settings to run StockSense")

with st.form("configuration_form", border=True):
    common_config_col, stockdb_config_col, app_config_col = st.tabs([
        "🏗️ Common",
        "🛢️ StockDB",
        "💻 App",
    ])

    # SECTION - Common Configuration
    with common_config_col:
        st.session_state.common = settings.common.model_copy()
        common_base_url = st.text_input(
            "Common Base URL",
            value=settings.common.base_url,
            help="Base URL for the APIs. Only change if you know what you are doing.",
        )
        st.session_state.common.base_url = common_base_url
        common_available_llm_providers = st.pills(
            "Available LLM Providers",
            options=settings.common.available_llm_providers,
            selection_mode="multi",
            default=settings.common.available_llm_providers,
            help="Select the LLM providers that you want to enable.",
        )
        st.session_state.common.available_llm_providers = common_available_llm_providers
        GROQ_API_KEY = st.text_input(
            "GROQ API Key",
            type="password",
            help="API key for GROQ service.",
            value=settings.common.GROQ_API_KEY,
        )
        st.session_state.common.GROQ_API_KEY = GROQ_API_KEY
        OPENAI_API_KEY = st.text_input(
            "OPENAI API Key",
            type="password",
            value=settings.common.OPENAI_API_KEY,
            help="API key for OpenAI ChatGPT service.",
        )
        st.session_state.common.OPENAI_API_KEY = OPENAI_API_KEY
        ANTHROPIC_API_KEY = st.text_input(
            "ANTHROPIC API Key",
            type="password",
            value=settings.common.ANTHROPIC_API_KEY,
            help="API key for Anthropic Claude service.",
        )
        st.session_state.common.ANTHROPIC_API_KEY = ANTHROPIC_API_KEY
        OLLAMA_API_KEY = st.text_input(
            "OLLAMA API Key",
            type="password",
            placeholder="Not Needed",
            value=settings.common.OLLAMA_API_KEY,
            help="OLLAMA runs locally, so no API key is needed. Leave blank if using local Ollama.",
        )
        st.session_state.common.OLLAMA_API_KEY = ""
        GOOGLE_API_KEY = st.text_input(
            "GOOGLE API Key",
            type="password",
            value=settings.common.GOOGLE_API_KEY,
            help="API key for Google Gemini service.",
        )
        st.session_state.common.GOOGLE_API_KEY = GOOGLE_API_KEY
        mlflow_port = st.number_input(
            "MLFlow Port",
            value=settings.common.mlflow_port,
            help="Port for MLFlow tracking server. Only change if you know what you are doing.",
        )
        st.session_state.common.mlflow_port = mlflow_port

    # SECTION - StockDB Configuration
    with stockdb_config_col:
        st.session_state.stockdb = settings.stockdb.model_copy()
        stockdb_port = st.number_input(
            "StockDB API Port",
            value=settings.stockdb.port,
            help="Port for StockDB API server. Only change if you know what you are doing.",
        )
        st.session_state.stockdb.port = stockdb_port
        # stockdb_data_base_path = st.text_input(
        #     "StockDB Data Base Path",
        #     value=settings.stockdb.data_base_path,
        #     help="Base path where StockDB stores its data. Only change if you know what you are doing.",
        # )
        # st.session_state.stockdb.data_base_path = (
        #     Path(stockdb_data_base_path).resolve().as_posix()
        # )
        stockdb_download_batch_size = st.number_input(
            "StockDB Download Batch Size",
            value=settings.stockdb.download_batch_size,
            min_value=20,
            max_value=100,
            help="Number of records to download in a single batch when downloading data. This is directly to your available RAM.",
        )
        st.session_state.stockdb.download_batch_size = stockdb_download_batch_size

    # SECTION - App Configuration
    with app_config_col:
        st.session_state.app = settings.app.model_copy()
        app_port = st.number_input(
            "App Port",
            value=settings.app.port,
            help="Port for the StockSense web application. Only change if you know what you are doing.",
        )
        st.session_state.app.port = app_port
        app_text_to_sql_model = st.text_input(
            "Text-to-SQL Model",
            value=settings.app.text_to_sql_model,
            help="LLM Model to use for text-to-SQL agent.",
        )
        st.session_state.app.text_to_sql_model = app_text_to_sql_model
        app_company_summary_model = st.text_input(
            "Company Summary Model",
            value=settings.app.company_summary_model,
            help="LLM Model to use for generating company summaries agent.",
        )
        st.session_state.app.company_summary_model = app_company_summary_model
        app_company_summary_qa_model = st.text_input(
            "Company Summary QA Model",
            value=settings.app.company_summary_qa_model,
            help="LLM Model to use for company summary question answering agent",
        )
        st.session_state.app.company_summary_qa_model = app_company_summary_qa_model

    submit_config = st.form_submit_button("Save Configuration", icon=":material/save:")

if submit_config:
    # Common settings
    settings.common.base_url = st.session_state.common.base_url
    settings.common.available_llm_providers = (
        st.session_state.common.available_llm_providers
    )
    settings.common.GROQ_API_KEY = st.session_state.common.GROQ_API_KEY
    settings.common.OPENAI_API_KEY = st.session_state.common.OPENAI_API_KEY
    settings.common.ANTHROPIC_API_KEY = st.session_state.common.ANTHROPIC_API_KEY
    settings.common.OLLAMA_API_KEY = st.session_state.common.OLLAMA_API_KEY
    settings.common.GOOGLE_API_KEY = st.session_state.common.GOOGLE_API_KEY
    settings.common.mlflow_port = st.session_state.common.mlflow_port
    # StockDB API settings
    settings.stockdb.port = st.session_state.stockdb.port
    # settings.stockdb.data_base_path = st.session_state.stockdb.data_base_path
    settings.stockdb.download_batch_size = st.session_state.stockdb.download_batch_size
    # Web App settings
    settings.app.port = st.session_state.app.port
    settings.app.text_to_sql_model = st.session_state.app.text_to_sql_model
    settings.app.company_summary_model = st.session_state.app.company_summary_model
    settings.app.company_summary_qa_model = (
        st.session_state.app.company_summary_qa_model
    )
    # saving the updated settings to config file
    settings.save_as_toml()
