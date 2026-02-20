from typing import Literal
import polars as pl
from pydantic import BaseModel
import reflex as rx
from httpx import AsyncClient
from stocksense.config import get_settings

settings = get_settings()


class CommonMixin(rx.State, mixin=True):
    """A mixin state for common StockDB data."""

    selected_exchange: str = ""
    selected_ticker: str | list[str] = []

    @rx.var
    async def available_exchanges(self) -> pl.DataFrame:
        """Get the available stock exchanges from StockDB.

        Returns:
            A DataFrame of available stock exchanges.
        """
        async with AsyncClient() as client:
            response = await client.get(
                f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security/",
                follow_redirects=True,
            )
            response.raise_for_status()
            # NOTE - response --> [exchange_symbol: exchange_name]
            exch_response = response.json()
            # NOTE - df --> | exch_symbol | exch_name | exch_name (exch_symbol) |
            return pl.DataFrame({
                "symbol": exch_response.keys(),
                "name": exch_response.values(),
            }).with_columns(dropdown=pl.col("name") + " (" + pl.col("symbol") + ")")

    @rx.var
    async def exchange_dropdown_list(self) -> list[str]:
        """Get the list of available exchanges for the dropdown."""
        df = await self.available_exchanges
        return df.select("dropdown").to_series().to_list()

    @rx.var
    async def available_tickers(self) -> dict[str, pl.DataFrame]:
        """Get the available tickers for each exchange"""
        async with AsyncClient() as client:
            response = await client.get(
                url=f"{settings.common.base_url}:{settings.stockdb.port}/api/bulk/list-tickers",
                follow_redirects=True,
            )
            # NOTE - response --> {exchange_symbol: [{ticker, company},...]}
            tickers_wrt_exchange = response.json()
            available_tickers = dict.fromkeys(
                tickers_wrt_exchange.keys(), pl.DataFrame()
            )

            for exch in available_tickers:
                if not tickers_wrt_exchange[exch]:
                    available_tickers[exch] = pl.DataFrame({
                        "ticker": [],
                        "company": [],
                    }).with_columns(dropdown=pl.lit(""))
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
            df
            .filter(pl.col("dropdown").is_in(dropdown_values))
            .select("ticker")
            .to_series()
            .to_list()
            #     if isinstance(dropdown_values, list)
            #     else df
            #     .filter(pl.col("dropdown") == dropdown_values)
            #     .select("ticker")
            #     .item()
        )

    async def get_ticker_history_columns(self) -> list[str]:
        """Fetch column names for the stock history table."""
        async with AsyncClient(timeout=None, follow_redirects=True) as client:
            response = await client.get(
                url=f"{settings.common.base_url}:{settings.stockdb.port}"
                f"/api/per-security/nse/tcs/history",
                params={"interval": "1d", "period": "1d"},
            )
            if response.status_code != 200:
                return []
            payload = response.json()
            return list(payload[0].keys()) if payload else []


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
        async with AsyncClient() as client:
            response = await client.get(
                f"{settings.common.base_url}:{settings.stockdb.port}/api/bulk/list-indexes"
            )
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
        async with AsyncClient() as client:
            # NOTE - response --> [{ticker, company},...]
            response = await client.get(
                url=f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security/{self.selected_exchange}/{self.index_choice}"
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

        self.messages.append(
            Message(role=role, content=content)
        )

        # Reset the prompt only if the message is from the user
        if role == "user":
            yield type(self).reset_prompt
