import asyncio
import logging

import polars as pl
import reflex as rx
import reflex_enterprise as rxe
from httpx import AsyncClient
from stocksense.ai.agents import StockDBContextDependency, text_to_sql
from stocksense.config import get_settings
from stocksense.types import DataInterval, DataPeriod

from webapp.state.shared import TickerSelectionMixin

logger = logging.getLogger("stocksense")
settings = get_settings()

POLARS_AG_GRID_FILTER_MAP = {
    pl.Int64: rxe.ag_grid.filters.number,
    pl.Float64: rxe.ag_grid.filters.number,
    pl.String: rxe.ag_grid.filters.text,
    pl.Boolean: rxe.ag_grid.filters.text,
    pl.Date: rxe.ag_grid.filters.date,
    pl.Datetime: rxe.ag_grid.filters.date,
}


class DataState(TickerSelectionMixin, rx.State):
    """State for the Playground → Data page (manual + AI workflows)."""

    # Manual form fields
    # Ticker selection fields are now in TickerSelectionMixin
    interval: str = DataInterval.ONE_DAY.value
    period: str = DataPeriod.SIX_MONTHS.value
    date_start: str = ""
    date_end: str = ""
    sql_query: str = ""
    preview_enabled: bool = True

    # TODO - add prompt cache/history

    # AI workflow fields
    ai_prompt: str = ""
    ai_generated_sql: str = ""
    ai_sql_query: str = ""
    ai_status_message: str = ""
    ai_status_steps: list[str] = []
    ai_is_generating: bool = False
    ai_error: str = ""

    # Submit state
    manual_submitted: bool = False
    fetch_data_ready: bool = False
    is_loading: bool = False
    _cancel_event: asyncio.Event = asyncio.Event()
    data: list[dict] = []
    columns_def: list[dict] = []

    @rx.event
    def set_interval(self, value: str):
        self.interval = value

    @rx.event
    def set_period(self, value: str):
        self.period = value

    @rx.event
    def set_date_start(self, value: str):
        self.date_start = value

    @rx.event
    def set_date_end(self, value: str):
        self.date_end = value

    @rx.event
    def set_sql_query(self, value: str):
        self.sql_query = value

    @rx.event
    def set_ai_prompt(self, value: str):
        self.ai_prompt = value
        self.ai_generated_sql = ""
        self.ai_sql_query = ""
        self.ai_status_message = ""
        self.ai_status_steps = []
        self.ai_error = ""

    @rx.event
    def set_ai_sql_query(self, value: str):
        self.ai_sql_query = value

    @rx.event
    def set_preview_enabled(self, value: bool):
        self.preview_enabled = value

    @rx.event
    def submit_manual(self):
        self.manual_submitted = True

    @rx.event
    def submit_ai(self):
        """Store AI SQL into the shared query field before fetching data."""
        self.sql_query = self.ai_sql_query
        self.manual_submitted = True

    @rx.event(background=True)
    async def fetch_data(self):
        """Fetch data based on the current state settings."""
        async with self:
            if self.is_loading:
                return
            self.is_loading = True
            self.fetch_data_ready = False
            self.ai_error = ""
            self.data = []
            self._cancel_event.clear()
            tickers = self.selected_ticker
            use_sql = bool(self.sql_query.strip())

        if use_sql:
            await self._fetch_via_sql_api()
        else:
            await self._fetch_via_ticker_api(tickers)

    async def _process_results(self, data: pl.LazyFrame):
        """Process and set results from a Polars DataFrame."""
        schema = data.collect_schema()
        column_def = [
            {
                "field": col,
                "filter": POLARS_AG_GRID_FILTER_MAP[schema[col]],
                "sortable": True,
            }
            for col in schema
        ]

        async with self:
            if not self._cancel_event.is_set():
                _ = await data.collect_async()
                self.data = _.to_dicts()
                self.columns_def = column_def
                self.fetch_data_ready = True
                self.is_loading = False

    async def _fetch_via_sql_api(self):
        """Fetch data using the SQL API (Dummy implementation)."""
        async with AsyncClient(timeout=None, follow_redirects=True) as client:
            response = await client.post(
                url=f"{settings.common.base_url}:{settings.stockdb.port}/api/bulk/query",
                json={
                    "exchange": self.selected_exchange,
                    "sql_query": self.sql_query,
                },
            )

            if response.is_error:
                async with self:
                    self.ai_error = f"Error fetching data: {response.text}"
                    self.is_loading = False
                return

            result = response.json()
            dummy_df = pl.LazyFrame(result)
        await self._process_results(dummy_df)

    @rx.event(background=True)
    async def generate_sql(self):
        """Generate SQL query from the AI prompt."""
        async with self:
            if self.ai_is_generating:
                return
            self.ai_is_generating = True
            self.ai_generated_sql = ""
            self.ai_sql_query = ""
            self.ai_error = ""
            self.ai_status_message = "Generating SQL query"
            self.ai_status_steps = ["Initializing text-to-SQL agent..."]

        try:
            columns = await self.get_ticker_history_columns()
            async with self:
                if not columns:
                    self.ai_error = "Unable to fetch table schema from StockDB."
                    self.ai_is_generating = False
                    self.ai_status_message = ""
                    return
                self.ai_status_steps.append("Fetched schema context from StockDB.")

            model_name = settings.app.text_to_sql_model
            api_key = getattr(
                settings.common,
                f"{model_name.split(':')[0].split('-')[0].upper()}_API_KEY",
                "",
            )
            if not api_key:
                async with self:
                    self.ai_error = "Missing API key for the text-to-SQL model."
                    self.ai_is_generating = False
                    self.ai_status_message = ""
                return

            async with self:
                self.ai_status_steps.append(f"Running model: {model_name}.")

            stockdb_ctx = StockDBContextDependency(columns=columns)
            agent = text_to_sql(model_name=model_name, api_key=api_key)
            result = await agent.run(self.ai_prompt, deps=stockdb_ctx)

            async with self:
                self.ai_generated_sql = result.output.sql_query
                self.ai_sql_query = result.output.sql_query
                self.ai_status_steps.append("SQL query generated successfully.")
                self.ai_is_generating = False
                self.ai_status_message = "SQL query generated successfully."
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            async with self:
                self.ai_error = "Failed to generate SQL query. Please try again."
                self.ai_is_generating = False
                self.ai_status_message = ""

    async def _fetch_via_ticker_api(self, tickers: list[str]):
        """Fetch data by iterating over tickers with throttling."""
        sem = asyncio.Semaphore(10)  # Throttling to 10 concurrent requests

        async def _inner_fetch(client: AsyncClient, ticker: str) -> dict:
            async with sem:
                if self._cancel_event.is_set():
                    return {}
                resp = await client.get(
                    url=f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security"
                    f"/{self.selected_exchange}/{ticker}/history",
                    params={"period": self.period, "interval": self.interval},
                )
                return resp.json()

        try:
            async with AsyncClient(timeout=None, follow_redirects=True) as client:
                async with asyncio.TaskGroup() as tg:
                    tasks = []
                    for ticker in tickers:
                        if self._cancel_event.is_set():
                            break
                        tasks.append(tg.create_task(_inner_fetch(client, ticker)))

                if self._cancel_event.is_set():
                    return

                results = [
                    pl.LazyFrame(task.result())
                    for task in tasks
                    if not task.cancelled() and len(task.result()) > 0
                ]

                if results:
                    data = pl.concat(results, how="vertical")
                    await self._process_results(data)
                else:
                    async with self:
                        self.is_loading = False
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            async with self:
                self.is_loading = False

    @rx.event
    def cancel_fetching(self):
        """Cancel the ongoing fetch operation."""
        self._cancel_event.set()
        self.is_loading = False
        self.data = []
        self.columns_def = []
        self.fetch_data_ready = False
