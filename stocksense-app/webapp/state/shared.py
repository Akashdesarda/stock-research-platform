import time
from typing import Optional

import polars as pl
import reflex as rx
from httpx import AsyncClient, HTTPError
from stocksense.config import get_settings

settings = get_settings()

# Cache TTL in seconds (5 minutes)
CACHE_TTL = 300


class CommonMixin(rx.State, mixin=True):
    """A mixin state for common StockDB data with caching and error handling."""

    selected_exchange: str = ""
    selected_ticker: list[str] = []

    # Cached data
    _cached_exchanges: Optional[pl.DataFrame] = None
    _cached_tickers: Optional[dict[str, pl.DataFrame]] = None
    _exchanges_cache_time: float = 0.0
    _tickers_cache_time: float = 0.0

    # Error state
    exchanges_error: str = ""
    tickers_error: str = ""
    is_loading_exchanges: bool = False
    is_loading_tickers: bool = False

    def _create_empty_exchanges_df(self) -> pl.DataFrame:
        """Create an empty DataFrame for exchanges.

        Returns:
            An empty DataFrame with the expected schema for exchanges.
        """
        return pl.DataFrame({"symbol": [], "name": [], "dropdown": []})

    @rx.var
    def available_exchanges(self) -> pl.DataFrame:
        """Get the cached available stock exchanges.

        Returns:
            A DataFrame of available stock exchanges, or empty DataFrame on error.
        """
        if self._cached_exchanges is not None:
            return self._cached_exchanges
        # Return empty DataFrame if no cache available
        return self._create_empty_exchanges_df()

    @rx.var
    def exchange_dropdown_list(self) -> list[str]:
        """Get the list of available exchanges for the dropdown."""
        df = self.available_exchanges
        if df.is_empty():
            return []
        return df.select("dropdown").to_series().to_list()

    @rx.var
    def available_tickers(self) -> dict[str, pl.DataFrame]:
        """Get the cached available tickers for each exchange.

        Returns:
            A dict mapping exchange symbols to DataFrames of tickers.
        """
        if self._cached_tickers is not None:
            return self._cached_tickers
        return {}

    @rx.var
    def ticker_dropdown_list(self) -> list[str]:
        """Get the list of available tickers for the selected exchange."""
        if not self.selected_exchange:
            return []
        tickers = self.available_tickers
        if self.selected_exchange not in tickers:
            return []
        df = tickers[self.selected_exchange]
        if df.is_empty():
            return []
        return df.select("dropdown").to_series().to_list()

    def _is_cache_valid(self, cache_time: float) -> bool:
        """Check if the cache is still valid based on TTL.

        Args:
            cache_time: The timestamp when the cache was last updated.

        Returns:
            True if cache is valid, False otherwise.
        """
        return (time.time() - cache_time) < CACHE_TTL

    @rx.event
    async def load_exchanges(self, force_refresh: bool = False):
        """Load exchanges from the API with caching and error handling.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data.
        """
        # Check cache validity
        if (
            not force_refresh
            and self._cached_exchanges is not None
            and self._is_cache_valid(self._exchanges_cache_time)
        ):
            return

        self.is_loading_exchanges = True
        self.exchanges_error = ""

        try:
            async with AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.common.base_url}:{settings.stockdb.port}/api/per-security/",
                    follow_redirects=True,
                )
                response.raise_for_status()
                # NOTE - response --> {exchange_symbol: exchange_name}
                exch_response = response.json()
                # NOTE - df --> | exch_symbol | exch_name | exch_name (exch_symbol) |
                self._cached_exchanges = pl.DataFrame({
                    "symbol": exch_response.keys(),
                    "name": exch_response.values(),
                }).with_columns(
                    dropdown=pl.col("name") + " (" + pl.col("symbol") + ")"
                )
                self._exchanges_cache_time = time.time()
        except HTTPError as e:
            self.exchanges_error = "Unable to load exchanges. Please check your connection and try again."
            # Keep existing cache if available
            if self._cached_exchanges is None:
                self._cached_exchanges = self._create_empty_exchanges_df()
        except Exception as e:
            self.exchanges_error = "An unexpected error occurred while loading exchanges."
            if self._cached_exchanges is None:
                self._cached_exchanges = self._create_empty_exchanges_df()
        finally:
            self.is_loading_exchanges = False

    @rx.event
    async def load_tickers(self, force_refresh: bool = False):
        """Load tickers from the API with caching and error handling.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data.
        """
        # Check cache validity
        if (
            not force_refresh
            and self._cached_tickers is not None
            and self._is_cache_valid(self._tickers_cache_time)
        ):
            return

        self.is_loading_tickers = True
        self.tickers_error = ""

        try:
            async with AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url=f"{settings.common.base_url}:{settings.stockdb.port}/api/bulk/list-tickers",
                    follow_redirects=True,
                )
                response.raise_for_status()
                # NOTE - response --> {exchange_symbol: [{ticker, company},...]}
                tickers_wrt_exchange = response.json()
                available_tickers = {}

                for exch in tickers_wrt_exchange.keys():
                    if not tickers_wrt_exchange[exch]:
                        available_tickers[exch] = pl.DataFrame({
                            "ticker": [],
                            "company": [],
                        }).with_columns(dropdown=pl.lit(""))
                    else:
                        available_tickers[exch] = pl.DataFrame(
                            tickers_wrt_exchange[exch]
                        ).with_columns(
                            dropdown=pl.col("ticker") + " - " + pl.col("company")
                        )
                # NOTE - available_tickers --> {exchange_symbol: df(ticker, company, ticker - company)}
                self._cached_tickers = available_tickers
                self._tickers_cache_time = time.time()
        except HTTPError as e:
            self.tickers_error = "Unable to load tickers. Please check your connection and try again."
            # Keep existing cache if available
            if self._cached_tickers is None:
                self._cached_tickers = {}
        except Exception as e:
            self.tickers_error = "An unexpected error occurred while loading tickers."
            if self._cached_tickers is None:
                self._cached_tickers = {}
        finally:
            self.is_loading_tickers = False

    @rx.event
    async def refresh_data(self):
        """Refresh both exchanges and tickers data."""
        await self.load_exchanges(force_refresh=True)
        await self.load_tickers(force_refresh=True)

    @rx.event
    async def get_exchange_symbol(self, dropdown_value: str):
        """Extract the exchange symbol from the dropdown value.

        Args:
            dropdown_value: The selected dropdown value.
        """
        # Ensure data is loaded
        await self.load_exchanges()

        df = self.available_exchanges
        if not df.is_empty():
            filtered = df.filter(pl.col("dropdown") == dropdown_value)
            if not filtered.is_empty():
                self.selected_exchange = filtered.select("symbol").item()

    @rx.event
    async def get_ticker_symbols(self, dropdown_values: list[str]):
        """Extract the ticker symbols from the dropdown values.

        Args:
            dropdown_values: The selected dropdown values.
        """
        # Ensure data is loaded
        await self.load_tickers()

        if not self.selected_exchange:
            self.selected_ticker = []
            return

        tickers = self.available_tickers
        if self.selected_exchange not in tickers:
            self.selected_ticker = []
            return

        df = tickers[self.selected_exchange]
        if not df.is_empty() and dropdown_values:
            self.selected_ticker = (
                df.filter(pl.col("dropdown").is_in(dropdown_values))
                .select("ticker")
                .to_series()
                .to_list()
            )
        else:
            self.selected_ticker = []
