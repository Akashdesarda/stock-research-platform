import asyncio

import polars as pl
import reflex as rx
import reflex_enterprise as rxe
from httpx import AsyncClient
from stocksense.config import get_settings
from stocksense.types import DataInterval, DataPeriod

from webapp.state.shared import CommonMixin

settings = get_settings()

POLARS_TO_AG_GRID_FILTER_TYPE_MAP = {
    pl.Int64: rxe.ag_grid.filters.number,
    pl.Float64: rxe.ag_grid.filters.number,
    pl.String: rxe.ag_grid.filters.text,
    pl.Boolean: rxe.ag_grid.filters.text,
    pl.Date: rxe.ag_grid.filters.date,
    pl.Datetime: rxe.ag_grid.filters.date,
}


class DataState(CommonMixin, rx.State):
    """State for the Playground → Data page (manual form only)."""

    # Manual form fields
    selected_exchange_dropdown: str = ""
    ticker_choice: str = "Index Based"
    selected_ticker_dropdowns: list[str] = []
    index_choice: str = ""
    selected_ticker: list[str] = []
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

    @rx.var
    async def exchange_wise_index(self) -> dict:
        async with AsyncClient() as client:
            response = await client.get(
                f"{settings.common.base_url}:{settings.stockdb.port}/api/bulk/list-indexes"
            )
            return response.json()

    @rx.var
    async def available_index(self) -> list[str]:
        _ = await self.exchange_wise_index
        return _.get(self.selected_exchange, [])

    @rx.event
    async def set_exchange_dropdown(self, value: str):
        self.selected_exchange_dropdown = value
        self.selected_ticker_dropdowns = []
        await self.get_exchange_symbol(value)

    @rx.event
    async def set_ticker_choice(self, value: str):
        self.ticker_choice = value

        # NOTE - for "All" committing right away
        if value == "All":
            _ = await self.available_tickers
            df = _[self.selected_exchange]
            self.selected_ticker = df.select("ticker").to_series().to_list()

    @rx.event
    async def set_index_choice(self, value: str):
        self.index_choice = value
        await self.get_tickers_for_index()

    @rx.event
    async def get_tickers_for_index(self):
        async with AsyncClient() as client:
            # NOTE - response --> [{ticker, company},...]
            response = await client.get(
                url=f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security/{self.selected_exchange}/{self.index_choice}"
            )
        self.selected_ticker = [i["ticker"] for i in response.json()]

    @rx.event
    async def get_tickers_for_desired(self, values: list[str]):
        self.selected_ticker_dropdowns = values
        await self.get_ticker_symbols(values)

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
        # TODO: Implement actual SQL API call
        dummy_df = pl.LazyFrame({
            "sql_result": ["Dummy Row 1", "Dummy Row 2"],
            "value": [100, 200],
        })
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
