import asyncio

import polars as pl
import reflex as rx
import reflex_enterprise as rxe
from httpx import AsyncClient
from stocksense.config import get_settings
from stocksense.types import DataInterval, DataPeriod

from webapp.state.shared import TickerSelectionMixin

settings = get_settings()

POLARS_TO_AG_GRID_FILTER_TYPE_MAP = {
    pl.Int64: rxe.ag_grid.filters.number,
    pl.Float64: rxe.ag_grid.filters.number,
    pl.String: rxe.ag_grid.filters.text,
    pl.Boolean: rxe.ag_grid.filters.text,
    pl.Date: rxe.ag_grid.filters.date,
    pl.Datetime: rxe.ag_grid.filters.date,
}


class DataState(TickerSelectionMixin, rx.State):
    """State for the Playground → Data page (manual form only)."""

    # Manual form fields
    # Ticker selection fields are now in TickerSelectionMixin
    interval: str = DataInterval.ONE_DAY.value
    period: str = DataPeriod.SIX_MONTHS.value
    date_start: str = ""
    date_end: str = ""
    sql_query: str = ""
    preview_enabled: bool = True

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
    def set_preview_enabled(self, value: bool):
        self.preview_enabled = value

    @rx.event
    def submit_manual(self):
        self.manual_submitted = True

    @rx.event(background=True)
    async def fetch_data(self):
        """Fetch data based on the current state settings."""
        async with self:
            if self.is_loading:
                return
            self.is_loading = True
            self.fetch_data_ready = False
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
                "filter": POLARS_TO_AG_GRID_FILTER_TYPE_MAP[schema[col]],
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
                url=f"{settings.common.base_url}:{settings.stockdb.port}/api/{self.selected_exchange}/query",
                json={"sql_query": self.sql_query},
            )
            result = response.json()
            dummy_df = pl.LazyFrame(result)
        await self._process_results(dummy_df)

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
        except Exception:
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
