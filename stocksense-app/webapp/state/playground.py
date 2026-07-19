import asyncio
import logging
import uuid
from typing import Any

import polars as pl
import reflex as rx
import reflex_enterprise as rxe
from agno.run import agent
from sqlglot import parse_one
from stocksense.config import get_settings
from stocksense.types import (
    DataInterval,
    DataPeriod,
)

from webapp.state.shared import AgentRunMixin, TickerSelectionMixin
from webapp.types import RunState, TraceStep

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


class DataState(AgentRunMixin, TickerSelectionMixin, rx.State):
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
    ai_sql_query: str = ""  # use for editing AI generated SQL
    ai_thinking_part: str = ""
    # TODO - add prompt cache/history

    # Submit state
    data: list[dict] = []
    columns_def: list[dict] = []
    manual_submitted: bool = False
    fetch_data_ready: bool = False
    run_state: str = RunState.idle.value  # for agent (text-to-SQL)
    fetch_state: str = RunState.idle.value  # for manual/SQL fetch flow
    _cancel_event: asyncio.Event = asyncio.Event()

    # Registered dataset state
    dataset_name: str = ""
    dataset_description: str = ""
    dataset_tags: list[str] = []
    register_dialog_open: bool = False

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
        self.agent_status_message = ""
        self.agent_error = ""

    @rx.event
    def set_ai_use_cache(self, value: bool):
        self.ai_use_cache = value
        if not value:
            self._record_step(
                TraceStep(
                    name="Cache disabled",
                    detail="Will generate new SQL on next generation",
                    icon="info",
                )
            )
        else:
            self._record_step(
                TraceStep(
                    name="Cache enabled",
                    detail="Will attempt to fetch from cache on next generation.",
                    icon="info",
                )
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
        self.fetch_state = RunState.cancelled.value
        self.data = []
        self.columns_def = []
        self.fetch_data_ready = False

    @rx.event
    def set_dataset_name(self, value: str):
        self.dataset_name = value

    @rx.event
    def set_dataset_description(self, value: str):
        self.dataset_description = value

    @rx.event
    def set_dataset_tags(self, value: list[str]):
        self.dataset_tags = value

    @rx.event
    def open_register_dialog(self):
        """Open the register dataset dialog when fetched data is available."""
        if self.fetch_data_ready and self.data:
            self.register_dialog_open = True

    @rx.event
    def close_register_dialog(self):
        """Close the register dataset dialog."""
        self.register_dialog_open = False

    @rx.event(background=True)
    async def fetch_data(self):
        """Fetch data based on the current state settings."""
        async with self:
            if self.fetch_state == RunState.generating.value:
                return
            self.fetch_state = RunState.generating.value
            self.fetch_data_ready = False
            self.agent_error = ""
            self.data = []
            self.dataset_tags = [self.index_choice] if self.index_choice else []
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
        if self.run_state == RunState.generating.value:
            # Guard: text-to-sql owns the busy window (manage_lifecycle=False), so this is the active re-entrancy check.
            return
        async with self:
            # Mark busy up front so the cache lookup below is also guarded against double-clicks.
            self.run_state = RunState.generating.value
            self.agent_error = ""
            self.agent_status_message = "Generating SQL query"
            self._reset_steps()
            self._record_step(
                TraceStep(
                    name="Initializing",
                    detail="Starting text-to-SQL agent",
                )
            )
            self.ai_generated_sql = ""
            self.ai_sql_query = ""
            self.ai_thinking_part = ""
            use_cache = self.ai_use_cache

        try:
            # Cache lookup (best-effort). Do not mutate the user's cache preference.
            if use_cache:
                async with self:
                    self._record_step(TraceStep(name="Checking prompt cache"))
                retrieved_cache = await self._fetch_cached_sql(self.ai_prompt)
                if retrieved_cache is not None:
                    cached_sql, cached_thinking = retrieved_cache
                    async with self:
                        self.ai_generated_sql = cached_sql
                        self.ai_sql_query = cached_sql
                        self.ai_thinking_part = cached_thinking
                        self._record_step(
                            TraceStep(
                                name="Fetched SQL from cache", icon="circle_check_big"
                            )
                        )
                        self.agent_status_message = (
                            "SQL query generated successfully (from cache)."
                        )
                    return

                async with self:
                    self._record_step(
                        TraceStep(
                            name="No cache entry found", detail="generating via model"
                        )
                    )

            await self.stream_agent_run(
                agent_id="text-to-sql",
                message=self.ai_prompt,
                dependencies={
                    "exchange": self.selected_exchange,
                    "ticker": self.selected_ticker,
                },
                on_content=None,
                on_complete=self._t2sql_on_completed,
                # manage_lifecycle=False: we already own the busy window (set at top, reset in finally) so the
                # mixin won't re-guard or re-reset and skip this stream.
                manage_lifecycle=False,
            )

        except Exception as e:
            logger.exception("Error generating SQL", exc_info=e)
            async with self:
                self.agent_error = (
                    f"Failed to generate SQL query due to error: {e}. Please try again."
                )
                self.agent_status_message = ""
                self._record_step(
                    TraceStep(
                        name="Generation failed",
                        detail=f"Error: {type(e).__name__}",
                        icon="circle_x",
                        passed=False,
                    )
                )

        finally:
            async with self:
                # We own lifecycle (manage_lifecycle=False), so clear busy ourselves once cache+stream are done.
                self.run_state = RunState.idle.value

    @rx.event
    async def register_dataset(self):
        """Register the resultant data as a dataset for regular future use"""
        if self.sql_query:
            logical_pan = {
                "exchange": self.selected_exchange,
                "sql_query": self.sql_query,
            }
        else:
            logical_pan = {
                "exchange": self.selected_exchange,
                "ticker": self.selected_ticker or None,
                "interval": self.interval or None,
                "period": None
                if (self.date_start and self.date_end)
                else (self.period or None),
                "start_date": self.date_start or None,
                "end_date": self.date_end or None,
            }
        payload = {
            "dataset_id": str(uuid.uuid4()),
            "name": self.dataset_name if len(self.dataset_name) > 0 else None,
            "description": self.dataset_description
            if len(self.dataset_description) > 0
            else None,
            "logical_plan": logical_pan,
            "tags": self.dataset_tags,
        }
        try:
            async with self._stockdb_client() as client:
                response = await client.put(
                    url="/operation/data/register", json=payload
                )
                response.raise_for_status()
                self.register_dialog_open = False
                return rx.toast.info(
                    "dataset has been registered successfully.",
                    position="bottom-right",
                )
        except Exception as e:
            logger.error(f"Error registering dataset: {e}")
            return rx.toast.error(
                f"Failed to register dataset due to error: {e}",
                position="bottom-right",
            )

    async def _fetch_cached_sql(self, prompt: str) -> tuple[str, str] | None:
        """Try to fetch cached SQL for a prompt"""
        try:
            async with self._stockdb_client() as client:
                response = await client.post(
                    url="/operation/prompt/search",
                    json={
                        "prompt": prompt,
                        "agent": "text-to-sql",
                        "cache_tier": "auto",
                    },
                )
            # Ensure non-2xx responses surface as HTTPStatusError
            response.raise_for_status()
            payload = response.json() or {}
            return payload.get("response", ""), payload.get("thinking", "")

        except Exception as e:
            logger.error(f"Cache lookup returned non-JSON due to {e}; treating as miss")

    async def _put_cache_generated_sql(self, prompt):
        """Put the generated SQL into the cache"""
        try:
            async with self._stockdb_client() as client:
                response = await client.put(
                    url="/operation/prompt/cache",
                    json={
                        "agent": "text-to-sql",
                        "prompt": prompt,
                        "model": settings.ai.text_to_sql_model,
                        "response": self.ai_generated_sql,
                        "thinking": self.ai_thinking_part,
                    },
                )
                # Ensure non-2xx responses surface as HTTPStatusError
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Cache update failed: {e}")

    async def _t2sql_on_completed(self, completed: agent.RunCompletedEvent):
        """Handle the final text-to-SQL result from the shared agent run"""
        content = completed.content or {}
        sql = parse_one(content.get("sql_query", "")).sql(dialect="duckdb", pretty=True)

        async with self:
            self.ai_thinking_part = completed.reasoning_content or self.ai_thinking_part
            self.ai_generated_sql = sql
            self.ai_sql_query = sql
            self._record_step(
                TraceStep(
                    name="SQL query generated successfully", icon="circle_check_big"
                )
            )
            self.agent_status_message = "SQL query generated successfully."

        if sql:
            await self._put_cache_generated_sql(self.ai_prompt)

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
                self.fetch_state = RunState.idle.value

    async def _fetch_via_sql_api(self):
        """Fetch data using the SQL API"""
        async with self._stockdb_client() as client:
            response = await client.post(
                url="/bulk/ticker/query",
                json={
                    "exchange": self.selected_exchange,
                    "sql_query": self.sql_query,
                },
            )
            if response.is_error:
                async with self:
                    self.agent_error = f"Error fetching data: {response.text}"
                    self.fetch_state = RunState.error.value
                return

            result = response.json()
            data = pl.LazyFrame(result)
        await self._process_results(data)

    async def _fetch_via_ticker_api(self, tickers: list[str], history_params: dict):
        """Fetch data by using Bulk history API"""
        try:
            async with self._stockdb_client() as client:
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
                self.fetch_state = RunState.error.value


DATASET_COLUMN_DEFS = [
    {
        "field": "dataset_id",
        "header_name": "Dataset ID",
        "width": 300,
        "cell_renderer": "agGroupCellRenderer",
        "filter": True,
        "enable_cell_text_selection": True,
    },
    {
        "field": "name",
        "header_name": "Name",
        "width": 200,
        "filter": True,
        "enable_cell_text_selection": True,
    },
    {
        "field": "description",
        "header_name": "Description",
        "flex": 1,
        "wrapText": True,
        "autoHeight": True,
        "filter": True,
        "enable_cell_text_selection": True,
    },
    {
        "field": "tags",
        "header_name": "Tags",
        "width": 150,
        "filter": True,
        "enable_cell_text_selection": True,
    },
    {
        "field": "last_modified",
        "header_name": "Last Modified",
        "width": 220,
        "filter": rxe.ag_grid.filters.date,
        "value_formatter": "params.value ? new Date(params.value).toLocaleString() : ''",
        "enable_cell_text_selection": True,
    },
]

DATASET_DETAIL_PARAMS = {
    "detail_grid_options": {
        "column_defs": [
            {"field": "key", "header_name": "Plan Property", "width": 200},
            {
                "field": "value",
                "header_name": "Value",
                "flex": 1,
                "wrapText": True,
                "autoHeight": True,
            },
        ]
    },
    "get_detail_row_data": lambda params: rx.vars.function.FunctionStringVar(
        "params.successCallback"
    ).call(params.data.logical_plan),
}


class RegisteredDatasetState(TickerSelectionMixin, rx.State):
    """State for viewing and editing registered dataset(s)."""

    columns_def: list[dict] = DATASET_COLUMN_DEFS
    _refresh_tick: int = 0

    selected_dataset_id: str = ""
    selected_dataset_ids: list[str] = []
    edit_dataset_name: str = ""
    edit_dataset_description: str = ""
    edit_dataset_tags: list[str] = []
    edit_dataset_logical_plan: dict[str, Any] = {}
    edit_dialog_open: bool = False
    edit_is_loading: bool = False

    interval: str = DataInterval.ONE_DAY.value
    period: str = DataPeriod.SIX_MONTHS.value
    date_start: str = ""
    date_end: str = ""
    sql_query: str = ""
    allow_ticker_choice: bool = True
    ticker_choice: str = "Index Based"
    desired_choice_as_multi_select: bool = True

    @rx.event
    def force_refresh(self):
        """Call this from a 'Refresh' button to reload data."""
        self._refresh_tick += 1

    @rx.event
    def set_selected_dataset_id(self, value: str):
        """Set the selected dataset id."""
        self.selected_dataset_id = value

    @rx.event
    def set_selected_dataset_ids(self, value: list[dict]):
        """Set selected dataset ids from grid row selection."""
        self.selected_dataset_ids = [
            str(row.get("dataset_id", "")) for row in value if row.get("dataset_id")
        ]
        self.selected_dataset_id = (
            self.selected_dataset_ids[0] if self.selected_dataset_ids else ""
        )

    @rx.event
    def set_edit_dataset_name(self, value: str):
        """Set the editable dataset name."""
        self.edit_dataset_name = value

    @rx.event
    def set_edit_dataset_description(self, value: str):
        """Set the editable dataset description."""
        self.edit_dataset_description = value

    @rx.event
    def set_edit_dataset_tags(self, value: list[str]):
        """Set the editable dataset tags."""
        self.edit_dataset_tags = value

    @rx.event
    def set_interval(self, value: str):
        """Set the logical plan interval."""
        self.interval = value

    @rx.event
    def set_period(self, value: str):
        """Set the logical plan period."""
        self.period = value

    @rx.event
    def set_date_start(self, value: str):
        """Set the logical plan start date."""
        self.date_start = value

    @rx.event
    def set_date_end(self, value: str):
        """Set the logical plan end date."""
        self.date_end = value

    @rx.event
    def set_sql_query(self, value: str):
        """Set the logical plan SQL query."""
        self.sql_query = value

    @rx.event
    def open_edit_dialog_for_dataset(self, dataset_id: str):
        """Set the selected dataset id before loading it for edit."""
        self.selected_dataset_id = dataset_id

    @rx.event
    async def edit_selected_dataset(self):
        """Load the currently selected dataset for editing."""
        if not self.selected_dataset_id:
            return rx.toast.warning(
                "Select a dataset row first.",
                position="bottom-right",
            )
        return await self.load_dataset_for_edit()

    @rx.event
    def close_edit_dialog(self):
        """Close the edit dialog."""
        self.edit_dialog_open = False

    @rx.event
    async def load_dataset_for_edit(self):
        """Fetch a dataset by id and prefill edit state."""
        if not self.selected_dataset_id:
            return rx.toast.warning(
                "Select a dataset id first.",
                position="bottom-right",
            )

        self.edit_is_loading = True
        try:
            async with self._stockdb_client() as client:
                response = await client.get(
                    f"/operation/data/{self.selected_dataset_id}"
                )
                response.raise_for_status()
                data = response.json()

            logical_plan = data.get("logical_plan") or {}
            exchange = logical_plan.get("exchange") or ""
            ticker = logical_plan.get("ticker") or []
            interval = logical_plan.get("interval") or DataInterval.ONE_DAY.value
            period = logical_plan.get("period") or DataPeriod.SIX_MONTHS.value
            start_date = logical_plan.get("start_date") or ""
            end_date = logical_plan.get("end_date") or ""
            sql_query = logical_plan.get("sql_query") or ""

            self.edit_dataset_name = data.get("name") or ""
            self.edit_dataset_description = data.get("description") or ""
            self.edit_dataset_tags = data.get("tags") or []
            self.edit_dataset_logical_plan = logical_plan

            self.selected_exchange = exchange
            self.selected_exchange_dropdown = ""
            if exchange:
                exchanges = await self.available_exchanges
                matched = exchanges.filter(pl.col("symbol") == exchange)
                if not matched.is_empty():
                    self.selected_exchange_dropdown = matched.select("dropdown").item()

            self.selected_ticker = ticker
            self.selected_ticker_dropdown = ""
            self.selected_ticker_dropdowns = []
            self.index_choice = ""
            self.interval = interval
            self.period = period
            self.date_start = start_date
            self.date_end = end_date
            self.sql_query = sql_query

            if sql_query:
                self.ticker_choice = "All"
            elif ticker:
                available_tickers = await self.available_tickers
                exchange_df = available_tickers.get(exchange)
                if exchange_df is not None and not exchange_df.is_empty():
                    matched_tickers = (
                        exchange_df
                        .filter(pl.col("ticker").is_in(ticker))
                        .select("dropdown")
                        .to_series()
                        .to_list()
                    )
                    self.selected_ticker_dropdowns = matched_tickers
                    self.selected_ticker_dropdown = (
                        matched_tickers[0] if matched_tickers else ""
                    )
                self.ticker_choice = "Desired"
            else:
                self.ticker_choice = "All"

            self.edit_dialog_open = True
        except Exception as e:
            logger.error(f"Error loading dataset for edit: {e}")
            return rx.toast.error(
                f"Failed to load dataset due to error: {e}",
                position="bottom-right",
            )
        finally:
            self.edit_is_loading = False

    @rx.event
    async def update_dataset(self):
        """Update an existing registered dataset."""
        if not self.selected_dataset_id:
            return rx.toast.warning(
                "No dataset selected for update.",
                position="bottom-right",
            )

        logical_plan = {
            "exchange": self.selected_exchange,
            "ticker": self.selected_ticker or None,
            "interval": None if self.sql_query.strip() else (self.interval or None),
            "period": None
            if self.sql_query.strip() or (self.date_start and self.date_end)
            else (self.period or None),
            "start_date": self.date_start or None,
            "end_date": self.date_end or None,
            "sql_query": self.sql_query or None,
        }

        payload = {
            "dataset_id": self.selected_dataset_id,
            "name": self.edit_dataset_name if len(self.edit_dataset_name) > 0 else None,
            "description": self.edit_dataset_description
            if len(self.edit_dataset_description) > 0
            else None,
            "logical_plan": logical_plan,
            "tags": self.edit_dataset_tags,
        }

        try:
            async with self._stockdb_client() as client:
                response = await client.put(
                    url="/operation/data/register",
                    json=payload,
                )
                response.raise_for_status()

            self.edit_dataset_logical_plan = logical_plan
            self.edit_dialog_open = False
            self._refresh_tick += 1
            return rx.toast.success(
                "Dataset updated successfully.",
                position="bottom-right",
            )
        except Exception as e:
            logger.error(f"Error updating dataset: {e}")
            return rx.toast.error(
                f"Failed to update dataset due to error: {e}",
                position="bottom-right",
            )

    @rx.var(cache=True)
    async def datasets(self) -> list[dict]:
        """Fetch registered datasets"""
        _ = self._refresh_tick
        try:
            async with self._stockdb_client() as client:
                response = await client.get("/operation/data")
                response.raise_for_status()
                data = response.json()

                formatted_data = []
                for i in data:
                    plan_dict = i.get("logical_plan", {})
                    plan_items = []
                    for k, v in plan_dict.items():
                        if v is not None:
                            if isinstance(v, list):
                                val_str = ", ".join(str(x) for x in v)
                            else:
                                val_str = str(v)
                            plan_items.append({"key": k, "value": val_str})

                    formatted_data.append({
                        "dataset_id": i.get("dataset_id", ""),
                        "name": i.get("name", ""),
                        "description": i.get("description") or "",
                        "logical_plan": plan_items,
                        "tags": ", ".join(i.get("tags") or []),
                        "last_modified": i.get("last_modified", ""),
                    })
                return formatted_data
        except Exception as e:
            logger.error(f"Error fetching registered datasets: {e}")
            return []
