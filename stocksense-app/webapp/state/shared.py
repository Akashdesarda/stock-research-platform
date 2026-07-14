import logging
from typing import Awaitable, Callable, Literal

import polars as pl
import reflex as rx
from agno.client import AgentOSClient
from agno.run import agent as agent_event
from httpx2 import AsyncClient, Timeout
from pydantic import BaseModel
from stocksense.config import get_settings

logger = logging.getLogger("stocksense")
settings = get_settings()


class CommonMixin(rx.State, mixin=True):
    """A mixin state for common StockDB data."""

    selected_exchange: str = ""
    selected_ticker: list[str] = []

    @rx.var
    async def available_exchanges(self) -> pl.DataFrame:
        """Get the available stock exchanges from StockDB.

        Returns:
            A DataFrame of available stock exchanges.
        """
        async with self._stockdb_client() as client:
            response = await client.get("/per-security")
            response.raise_for_status()
            # NOTE - response --> [exchange_symbol: exchange_name]
            exch_response = response.json()
            # NOTE - df --> | exch_symbol | exch_name | exch_name (exch_symbol) |
            return pl.DataFrame(
                {
                    "symbol": exch_response.keys(),
                    "name": exch_response.values(),
                }
            ).with_columns(dropdown=pl.col("name") + " (" + pl.col("symbol") + ")")

    @rx.var
    async def exchange_dropdown_list(self) -> list[str]:
        """Get the list of available exchanges for the dropdown."""
        df = await self.available_exchanges
        return df.select("dropdown").to_series().to_list()

    @rx.var
    async def available_tickers(self) -> dict[str, pl.DataFrame]:
        """Get the available tickers for each exchange"""
        async with self._stockdb_client() as client:
            response = await client.get("/bulk/list-tickers")
            # NOTE - response --> {exchange_symbol: [{ticker, company},...]}
            tickers_wrt_exchange = response.json()
            available_tickers = dict.fromkeys(
                tickers_wrt_exchange.keys(), pl.DataFrame()
            )

            for exch in available_tickers:
                if not tickers_wrt_exchange[exch]:
                    available_tickers[exch] = pl.DataFrame(
                        {
                            "ticker": [],
                            "company": [],
                        }
                    ).with_columns(dropdown=pl.lit(""))
                else:
                    available_tickers[exch] = pl.DataFrame(tickers_wrt_exchange[exch])
                    available_tickers[exch] = available_tickers[exch].with_columns(
                        dropdown=pl.col("ticker") + " - " + pl.col("company")
                    )
            # NOTE - available_tickers --> {exchange_symbol: df(ticker, company, ticker - company)}
            return available_tickers

    @rx.var
    async def ticker_dropdown_list(self) -> list[str]:
        """Get the list of available tickers for the selected exchange."""
        _ = await self.available_tickers
        if not self.selected_exchange or self.selected_exchange not in _:
            return []
        df = _[self.selected_exchange]
        return df.select("dropdown").to_series().to_list()

    @rx.event
    async def get_exchange_symbol(self, dropdown_value: str):
        """Extract the exchange symbol from the dropdown value.

        Args:
            dropdown_value: The selected dropdown value.
        Returns:
            The exchange symbol.
        """
        _ = await self.available_exchanges
        self.selected_exchange = (
            _.filter(pl.col("dropdown") == dropdown_value).select("symbol").item()
        )

    @rx.event
    async def get_ticker_symbols(self, dropdown_values: list[str]):
        """Extract the ticker symbols from the dropdown values.

        Args:
            dropdown_values: The selected dropdown values.
        Returns:
            The list of ticker symbols.
        """
        _ = await self.available_tickers
        df = _[self.selected_exchange]
        self.selected_ticker = (
            df.filter(pl.col("dropdown").is_in(dropdown_values))
            .select("ticker")
            .to_series()
            .to_list()
        )

    async def get_ticker_history_columns(self) -> list[str]:
        """Fetch column names for the stock history table."""
        async with self._stockdb_client() as client:
            response = await client.get(
                url="/per-security/nse/tcs/history",
                params={"interval": "1d", "period": "1d"},
            )
            if response.status_code != 200:
                return []
            payload = response.json()
            return list(payload[0].keys()) if payload else []

    def _stockdb_client(self) -> AsyncClient:
        """Return a configured httpx AsyncClient."""
        return AsyncClient(
            timeout=Timeout(connect=5, read=120, write=120),
            follow_redirects=True,
            base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api",
        )


class TickerSelectionMixin(CommonMixin, mixin=True):
    """Mixin for interactive ticker selection state logic."""

    # Form fields
    selected_exchange_dropdown: str = ""
    allow_ticker_choice: bool = True
    ticker_choice: str = "Index Based"
    selected_ticker_dropdown: str = ""
    selected_ticker_dropdowns: list[str] = []
    index_choice: str = ""
    desired_choice_as_multi_select: bool = True

    @rx.var
    async def exchange_wise_index(self) -> dict:
        async with self._stockdb_client() as client:
            response = await client.get("/bulk/list-indexes")
            return response.json()

    @rx.var
    async def available_index(self) -> list[str]:
        _ = await self.exchange_wise_index
        # NOTE: self.selected_exchange comes from CommonMixin
        return _.get(self.selected_exchange, [])

    @rx.event
    async def set_exchange_dropdown(self, value: str):
        self.selected_exchange_dropdown = value
        self.selected_ticker_dropdown = ""
        self.selected_ticker_dropdowns = []
        self.selected_ticker = []
        self.index_choice = ""
        # NOTE: get_exchange_symbol comes from CommonMixin
        await self.get_exchange_symbol(value)

    @rx.event
    async def set_ticker_choice(self, value: str):
        self.ticker_choice = value

        # NOTE - for "All" committing right away
        if value == "All":
            # NOTE: available_tickers comes from CommonMixin
            _ = await self.available_tickers
            df = _[self.selected_exchange]
            self.selected_ticker = df.select("ticker").to_series().to_list()
        else:
            self.selected_ticker = []

    @rx.event
    async def set_index_choice(self, value: str):
        self.index_choice = value
        await self.get_tickers_for_index()

    @rx.event
    async def get_tickers_for_index(self):
        async with self._stockdb_client() as client:
            # NOTE - response --> [{ticker, company},...]
            response = await client.get(
                f"/per-security/{self.selected_exchange}/{self.index_choice}"
            )
        self.selected_ticker = [i["ticker"] for i in response.json()]

    @rx.event
    async def get_tickers_for_desired(self, values: list[str] | str):
        if isinstance(values, str):
            normalized_values = [values] if values else []
            self.selected_ticker_dropdown = values
        else:
            normalized_values = values
            self.selected_ticker_dropdown = values[0] if values else ""

        self.selected_ticker_dropdowns = normalized_values
        # NOTE: get_ticker_symbols comes from CommonMixin
        await self.get_ticker_symbols(normalized_values)


class Message(BaseModel):
    role: str
    content: str


class ChatMixin(rx.State, mixin=True):
    """A mixin state for common chat data."""

    prompt: str = ""
    messages: list[Message] = []
    is_loading: bool = False

    @rx.event
    def set_prompt(self, value: str):
        self.prompt = value

    @rx.event
    def reset_prompt(self):
        self.prompt = ""
        self.is_loading = True

    @rx.event
    async def append_message(self, role: Literal["user", "assistant"], content: str):
        if not content.strip():
            return

        self.messages.append(Message(role=role, content=content))

        # Reset the prompt only if the message is from the user
        if role == "user":
            yield type(self).reset_prompt


class AgentRunMixin(rx.State, mixin=True):
    """A mixin state for common agent run data."""

    agent_is_generating: bool = False  # Single busy flag: drives the spinner, disables the button, gates cancel, and prevents overlapping runs.
    agent_run_id: str = ""
    agent_error: str = ""
    agent_status_message: str = ""
    agent_steps: list[str] = []

    _active_agent_id: str = ""

    async def agent_run(self, **kwargs) -> agent_event.RunOutput:
        async with self:
            self._active_agent_id = kwargs["agent_id"]
        try:
            client = self._ai_client()
            run_output = await client.run_agent(**kwargs)
            async with self:
                self.agent_run_id = run_output.run_id
            return run_output

        except Exception as e:
            logger.exception("Agent stream failed", exc_info=e)
            async with self:
                self.agent_error = f"Failed to generate due to error: {e}."
            # Re-raise to preserve return type contract
            raise

    async def stream_agent_run(
        self,
        on_content: Callable[[agent_event.RunContentEvent], Awaitable[None]]
        | None = None,
        on_complete: Callable[[agent_event.RunCompletedEvent], Awaitable[None]]
        | None = None,
        manage_lifecycle: bool = True,
        **kwargs,
    ):
        async with self:
            # Record the active agent id up front (always, regardless of lifecycle mode) so
            # cancel_agent_run can target the right run even when manage_lifecycle=False.
            self._active_agent_id = kwargs["agent_id"]

        if manage_lifecycle:
            # manage_lifecycle=True: the mixin owns the agent_is_generating window (sets/resets + guards).
            # manage_lifecycle=False: the caller owns it (e.g. to wrap pre-stream work like cache lookup).
            if self.agent_is_generating:
                # Guard: a run is already in flight, ignore the new request (prevents overlapping runs).
                return

            # Update UI state before starting the agent run
            async with self:
                # Mark busy: flips button to disabled + shows spinner in the UI.
                self.agent_is_generating = True
                self.agent_error = ""
                self.agent_status_message = "Generating…"
                self.agent_steps = []
                self.agent_run_id = ""

        try:
            client = self._ai_client()
            completed = None

            async for event in client.run_agent_stream(**kwargs):
                if isinstance(event, agent_event.RunStartedEvent):
                    async with self:
                        self.agent_run_id = event.run_id
                        self.agent_steps.append(f"Running model: {event.model}")
                        logger.debug(
                            f"using model {event.model} for agent: {event.agent_id} with run_id: {self.agent_run_id}"
                        )
                # Tool calling events - guard against None tool
                elif isinstance(event, agent_event.ToolCallStartedEvent):
                    if event.tool and event.tool.tool_name:
                        async with self:
                            self.agent_steps.append(
                                f"Calling tool {event.tool.tool_name}"
                            )
                elif isinstance(event, agent_event.ToolCallCompletedEvent):
                    if event.tool and event.tool.tool_name:
                        async with self:
                            self.agent_steps.append(
                                f"Tool {event.tool.tool_name} completed"
                            )
                elif isinstance(event, agent_event.ToolCallErrorEvent):
                    if event.tool and event.tool.tool_name:
                        async with self:
                            self.agent_steps.append(
                                f"Tool {event.tool.tool_name} failed"
                            )
                # Content delta event
                elif isinstance(event, agent_event.RunContentEvent):
                    if on_content:
                        await on_content(event)
                # Cancellation event
                elif isinstance(event, agent_event.RunCancelledEvent):
                    async with self:
                        self.agent_status_message = "Request Cancelled"
                        self.agent_steps.append(f"Run cancelled: {event.reason or ''}")
                    return
                # Error event
                elif isinstance(event, agent_event.RunErrorEvent):
                    async with self:
                        self.agent_error = (
                            f"Agent run failed: {event.content or event.error_type}"
                        )
                        self.agent_status_message = (
                            "Generation failed. Please try again later."
                        )
                    return
                # Completion event
                elif isinstance(event, agent_event.RunCompletedEvent):
                    completed = event
                    logger.debug(f"{completed.run_id} agent run completed successfully")

            # processing the completion event
            if completed is None:
                async with self:
                    self.agent_error = "Generation ended without a completion event."
                    self.agent_status_message = "Generation failed."
                return
            if on_complete:
                await on_complete(completed)

        except Exception as e:
            logger.exception("Agent stream failed", exc_info=e)
            async with self:
                self.agent_error = f"Failed to generate due to error: {e}."
                self.agent_status_message = ""

        finally:
            if manage_lifecycle:
                async with self:
                    # Clear busy: re-enables the button and flips the spinner to the check icon.
                    self.agent_is_generating = False

    @rx.event
    async def cancel_agent_run(self):
        """Request server-side cancellation of the active run."""
        if not self.agent_is_generating or not self.agent_run_id:
            # No live run (or no run id yet) — nothing to cancel, so this is a no-op.
            return
        try:
            client = self._ai_client()
            await client.cancel_agent_run(
                agent_id=self._active_agent_id,
                run_id=self.agent_run_id,
            )
            async with self:
                self.agent_steps.append("Cancellation requested")
        except Exception as e:
            logger.error("Cancel request failed", exc_info=e)
            async with self:
                self.agent_error = f"Failed to cancel run: {e}"

    def _ai_client(self) -> AgentOSClient:
        return AgentOSClient(f"{settings.ai.ai_url}:{settings.ai.port}")
