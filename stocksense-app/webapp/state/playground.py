import asyncio
import logging
import uuid

import polars as pl
import reflex as rx
import reflex_enterprise as rxe
from httpx import AsyncClient, DecodingError
from stocksense.config import get_settings
from stocksense.types import AgentStructuredResponse, DataInterval, DataPeriod

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
    interval: str = DataInterval.ONE_DAY.value
    period: str = DataPeriod.SIX_MONTHS.value
    date_start: str = ""
    date_end: str = ""
    sql_query: str = ""
    preview_enabled: bool = True

    # AI workflow fields
    ai_use_cache: bool = True
    ai_prompt: str = ""
    ai_generated_sql: str = ""
    ai_sql_query: str = ""
    ai_thinking_part: str = ""
    ai_status_message: str = ""
    ai_status_steps: list[str] = []
    ai_is_generating: bool = False
    ai_error: str = ""
    # TODO - add prompt cache/history

    # Submit state
    data: list[dict] = []
    columns_def: list[dict] = []
    manual_submitted: bool = False
    fetch_data_ready: bool = False
    is_loading: bool = False
    _cancel_event: asyncio.Event = asyncio.Event()

    def _client(self) -> AsyncClient:
        """Return a configured httpx AsyncClient."""
        return AsyncClient(
            timeout=None,
            follow_redirects=True,
            base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api",
        )

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
    def set_ai_use_cache(self, value: bool):
        self.ai_use_cache = value
        if not value:
            self.ai_status_steps.append(
                "Cache disabled, will generate new SQL on next generation."
            )
        else:
            self.ai_status_steps.append(
                "Cache enabled, will attempt to fetch from cache on next generation."
            )

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

    @rx.event
    def cancel_fetching(self):
        """Cancel the ongoing fetch operation."""
        self._cancel_event.set()
        self.is_loading = False
        self.data = []
        self.columns_def = []
        self.fetch_data_ready = False

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
            if self.date_start and self.date_end:
                history_params = {
                    "interval": self.interval,
                    "start_date": self.date_start,
                    "end_date": self.date_end,
                }
            else:
                history_params = {
                    "interval": self.interval,
                    "period": self.period,
                }

        if use_sql:
            await self._fetch_via_sql_api()
        else:
            await self._fetch_via_ticker_api(tickers, history_params)

    @rx.event(background=True)
    async def generate_text_to_sql(self):
        """Generate SQL query from the AI prompt."""
        async with self:
            if self.ai_is_generating:
                return
            self.ai_is_generating = True
            self.ai_generated_sql = ""
            self.ai_sql_query = ""
            self.ai_thinking_part = ""
            self.ai_error = ""
            self.ai_status_message = "Generating SQL query"
            self.ai_status_steps = ["Initializing text-to-SQL agent..."]

            use_cache = bool(self.ai_use_cache)

        try:
            # Cache lookup (best-effort). Do not mutate the user's cache preference.
            if use_cache:
                async with self:
                    self.ai_status_steps.append("Checking prompt cache...")
                retrieved_cache = await self._try_fetch_cached_sql(
                    self.ai_prompt
                )
                if retrieved_cache is not None:
                    cached_sql, cached_thinking = retrieved_cache
                    async with self:
                        self.ai_generated_sql = cached_sql
                        self.ai_sql_query = cached_sql
                        self.ai_thinking_part = cached_thinking
                        self.ai_status_steps.append("Fetched SQL from cache.")
                        self.ai_status_message = (
                            "SQL query generated successfully (from cache)."
                        )
                    return

                async with self:
                    self.ai_status_steps.append(
                        "No cache entry found; generating via model."
                    )

            await self._generate_sql_via_llm(self.ai_prompt)

        except Exception as e:
            logger.exception("Error generating SQL")
            async with self:
                self.ai_error = (
                    "Failed to generate SQL query. Please try again."
                )
                self.ai_status_message = ""
                self.ai_status_steps.append(
                    f"Generation failed: {type(e).__name__}"
                )

        finally:
            async with self:
                self.ai_is_generating = False

    async def _try_fetch_cached_sql(
        self, prompt: str
    ) -> tuple[str, str] | None:
        """Try to fetch cached SQL for a prompt"""
        try:
            async with self._client() as client:
                response = await client.post(
                    url="/operation/prompt/search",
                    json={
                        "prompt": prompt,
                        "agent": "text-to-sql",
                        "cache_tier": "auto",
                    },
                )
            if response.status_code == 200:
                payload = response.json() or {}
                return payload.get("response", ""), payload.get("thinking", "")
            else:
                logger.warning(
                    f"Cannot fetch cached SQL due to HTTP status: {response.status_code}"
                )
        except DecodingError:
            logger.warning("Cache lookup returned non-JSON; treating as miss")

    async def _generate_sql_via_llm(self, prompt: str):
        """Generate SQL using the LLM agent"""
        async with self:
            self.ai_status_steps.append(
                f"Running model: {settings.ai.text_to_sql_model}."
            )

        # send the request
        try:
            async with self._client() as client:
                response = await client.post(
                    "/agent/text-to-sql",
                    json={
                        "prompt": prompt,
                        "model": settings.ai.text_to_sql_model,
                        "exchange": self.selected_exchange,
                        "session_id": str(uuid.uuid4()),
                    },
                )
                result = AgentStructuredResponse.model_validate(response.json())
        except Exception as e:
            logger.error(f"Error during LLM generation: {e}")
            async with self:
                self.ai_error = f"Error during LLM generation: {e}"
                self.ai_status_message = ""
                return

        # updating UI state with LLM response
        async with self:
            self.ai_thinking_part = result.thinking or ""
            self.ai_generated_sql = result.content.get("sql_query", "")
            self.ai_sql_query = result.content.get("sql_query", "")
            # TODO - add tool calls to steps
            self.ai_status_steps.append("SQL query generated successfully.")
            self.ai_status_message = "SQL query generated successfully."

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
        """Fetch data using the SQL API"""
        async with self._client() as client:
            response = await client.post(
                url="/bulk/ticker/query",
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
            data = pl.LazyFrame(result)
        await self._process_results(data)

    async def _fetch_via_ticker_api(
        self, tickers: list[str], history_params: dict
    ):
        """Fetch data by using Bulk history API"""
        try:
            async with self._client() as client:
                resp = await client.post(
                    url="/bulk/ticker/history",
                    json={
                        "exchange": self.selected_exchange,
                        "ticker": tickers,
                        **history_params,
                    },
                )
                resp.raise_for_status()
                data = pl.LazyFrame(resp.json())
                await self._process_results(data)
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            async with self:
                self.is_loading = False
