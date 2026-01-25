import polars as pl
import reflex as rx
from httpx import AsyncClient
from stocksense.config import get_settings

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
            df.filter(pl.col("dropdown").is_in(dropdown_values))
            .select("ticker")
            .to_series()
            .to_list()
        )
