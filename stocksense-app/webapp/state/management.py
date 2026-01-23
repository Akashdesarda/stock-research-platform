from datetime import datetime

import reflex as rx
from httpx import AsyncClient
from stocksense.config import get_settings

from webapp.state.shared import CommonMixin

settings = get_settings()


class ConfigurationState(rx.State):
    """Application configuration state."""

    # Common settings
    common_base_url: str = settings.common.base_url
    common_available_llm_providers: list[str] = settings.common.available_llm_providers
    llm_providers_to_use: list[str] = settings.common.available_llm_providers
    common_available_llm_providers_csv: str = ", ".join(
        settings.common.available_llm_providers
    )
    common_GROQ_API_KEY: str = settings.common.GROQ_API_KEY
    common_OPENAI_API_KEY: str = settings.common.OPENAI_API_KEY
    common_ANTHROPIC_API_KEY: str = settings.common.ANTHROPIC_API_KEY
    common_OLLAMA_API_KEY: str = settings.common.OLLAMA_API_KEY
    common_GOOGLE_API_KEY: str = settings.common.GOOGLE_API_KEY
    common_mlflow_port: int = settings.common.mlflow_port

    # StockDB settings
    stockdb_port: int = settings.stockdb.port
    # stockdb_data_base_path: str = settings.stockdb.data_base_path.as_posix()
    stockdb_download_batch_size: int = settings.stockdb.download_batch_size

    # App settings
    app_port: int = settings.app.port
    app_text_to_sql_model: str = settings.app.text_to_sql_model
    app_company_summary_model: str = settings.app.company_summary_model
    app_company_summary_qa_model: str = settings.app.company_summary_qa_model

    # UI helpers
    last_saved: str = ""
    save_error: str = ""

    # Setters (explicit for type checking + coercion)
    def set_common_base_url(self, value: str) -> None:
        self.common_base_url = value

    @rx.event
    def update_base_url(self, value: str):
        self.common_base_url = value

    @rx.event
    def update_llm_providers(self, value: list[str]):
        self.llm_providers_to_use = value

    @rx.event
    def update_groq_api_key(self, value: str):
        self.common_GROQ_API_KEY = value

    @rx.event
    def update_openai_api_key(self, value: str):
        self.common_OPENAI_API_KEY = value

    @rx.event
    def update_anthropic_api_key(self, value: str):
        self.common_ANTHROPIC_API_KEY = value

    @rx.event
    def update_ollama_api_key(self, value: str):
        self.common_OLLAMA_API_KEY = value

    @rx.event
    def update_google_api_key(self, value: str):
        self.common_GOOGLE_API_KEY = value

    @rx.event
    def update_mlflow_port(self, value: int | str):
        self.common_mlflow_port = int(value)

    @rx.event
    def update_stockdb_port(self, value: int | str):
        self.stockdb_port = int(value)

    # @rx.event
    # def update_stockdb_data_base_path(self, value: str):
    #     self.stockdb_data_base_path = value

    @rx.event
    def update_stockdb_download_batch_size(self, value: int | str):
        self.stockdb_download_batch_size = int(value)

    @rx.event
    def update_app_port(self, value: int | str):
        self.app_port = int(value)

    @rx.event
    def update_app_text_to_sql_model(self, value: str):
        self.app_text_to_sql_model = value

    @rx.event
    def update_app_company_summary_model(self, value: str):
        self.app_company_summary_model = value

    @rx.event
    def update_app_company_summary_qa_model(self, value: str):
        self.app_company_summary_qa_model = value

    def reload_from_disk(self) -> None:
        """Reload config.toml from disk and refresh state values."""
        global settings
        settings = get_settings()

        self.common_base_url = settings.common.base_url
        self.common_available_llm_providers = list(
            settings.common.available_llm_providers
        )
        self.common_available_llm_providers_csv = ", ".join(
            settings.common.available_llm_providers
        )
        self.common_GROQ_API_KEY = settings.common.GROQ_API_KEY
        self.common_OPENAI_API_KEY = settings.common.OPENAI_API_KEY
        self.common_ANTHROPIC_API_KEY = settings.common.ANTHROPIC_API_KEY
        self.common_OLLAMA_API_KEY = settings.common.OLLAMA_API_KEY
        self.common_GOOGLE_API_KEY = settings.common.GOOGLE_API_KEY
        self.common_mlflow_port = settings.common.mlflow_port

        self.stockdb_port = settings.stockdb.port
        # self.stockdb_data_base_path = settings.stockdb.data_base_path.as_posix()
        self.stockdb_download_batch_size = settings.stockdb.download_batch_size

        self.app_port = settings.app.port
        self.app_text_to_sql_model = settings.app.text_to_sql_model
        self.app_company_summary_model = settings.app.company_summary_model
        self.app_company_summary_qa_model = settings.app.company_summary_qa_model

        self.save_error = ""

    @rx.event
    def update_config(self) -> None:
        """Update the current configuration to the settings"""
        try:
            # Update settings for runtime usage
            settings.common.base_url = self.common_base_url
            settings.common.available_llm_providers = (
                self.common_available_llm_providers
            )
            settings.common.GROQ_API_KEY = self.common_GROQ_API_KEY
            settings.common.OPENAI_API_KEY = self.common_OPENAI_API_KEY
            settings.common.ANTHROPIC_API_KEY = self.common_ANTHROPIC_API_KEY
            settings.common.OLLAMA_API_KEY = self.common_OLLAMA_API_KEY
            settings.common.GOOGLE_API_KEY = self.common_GOOGLE_API_KEY
            settings.common.mlflow_port = self.common_mlflow_port

            settings.stockdb.port = self.stockdb_port
            # settings.stockdb.data_base_path = self.stockdb_data_base_path
            settings.stockdb.download_batch_size = self.stockdb_download_batch_size

            settings.app.port = self.app_port
            settings.app.text_to_sql_model = self.app_text_to_sql_model
            settings.app.company_summary_model = self.app_company_summary_model
            settings.app.company_summary_qa_model = self.app_company_summary_qa_model

            # update the config file
            settings.save_as_toml()

            self.last_saved = datetime.now().isoformat(timespec="seconds")
            self.save_error = ""
        except Exception as exc:  # pragma: no cover
            self.save_error = str(exc)
            self.last_saved = ""


class TaskState(CommonMixin, rx.State):
    """State for management task execution."""

    task_mode: str = "auto"
    download_mode: str = "incremental"
    selected_exchange_dropdown: str = ""
    selected_ticker_dropdowns: list[str] = []
    start_date: str = ""
    end_date: str = ""

    is_submitting: bool = False
    submit_success: str = ""
    submit_error: str = ""

    @rx.event
    def set_task_mode(self, value: str):
        self.task_mode = value
        self.submit_success = ""
        self.submit_error = ""

        if value == "auto":
            self.selected_ticker_dropdowns = []
            self.selected_ticker = []
            self.start_date = ""
            self.end_date = ""

    @rx.event
    def set_download_mode(self, value: str):
        self.download_mode = value
        self.submit_success = ""
        self.submit_error = ""

    @rx.event
    async def set_exchange_dropdown(self, value: str):
        self.selected_exchange_dropdown = value
        await self.get_exchange_symbol(value)
        self.selected_ticker_dropdowns = []
        self.selected_ticker = []

    @rx.event
    async def set_ticker_dropdowns(self, values: list[str]):
        self.selected_ticker_dropdowns = values
        await self.get_ticker_symbols(values)

    @rx.event
    def set_start_date(self, value: str):
        self.start_date = value

    @rx.event
    def set_end_date(self, value: str):
        self.end_date = value

    @rx.event(background=True)
    async def submit_task(self):
        async with self:
            self.is_submitting = True
            self.submit_error = ""
            self.submit_success = ""

        try:
            payload = {
                "task_mode": self.task_mode,
                "download_mode": self.download_mode,
                "exchange": self.selected_exchange,
                "ticker": self.selected_ticker if self.task_mode == "manual" else None,
                "start_date": self.start_date if self.task_mode == "manual" else None,
                "end_date": self.end_date if self.task_mode == "manual" else None,
            }

            url = (
                f"{settings.common.base_url}:{settings.stockdb.port}"
                "/api/task/ticker/history"
            )

            async with AsyncClient(follow_redirects=True, timeout=300) as client:
                response = await client.post(url, json=payload)

            async with self:
                if response.status_code == 200:
                    self.submit_success = "Data update task successfully completed!"
                else:
                    detail = "Request failed."
                    try:
                        payload = response.json()
                        detail = str(payload.get("detail", detail))
                    except Exception:  # pragma: no cover
                        detail = response.text or detail
                    self.submit_error = detail
        except Exception as exc:  # pragma: no cover
            async with self:
                self.submit_error = str(exc)
        finally:
            async with self:
                self.is_submitting = False
