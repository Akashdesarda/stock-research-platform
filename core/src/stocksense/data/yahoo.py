import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

import polars as pl

from stocksense.types import DataInterval, DataPeriod, StockExchangeYahooIdentifier

logger = logging.getLogger("stocksense")

if TYPE_CHECKING:
    import yfinance as yf


def _require_yfinance():
    try:
        import yfinance as yf
    except ModuleNotFoundError as e:
        raise ImportError(
            "YFStockData requires optional dependency 'yfinance'. Install the 'data' extra, e.g.\n"
            '  pip install "Stocksense-Core[data]"\n'
            "or (uv)\n"
            '  uv add "Stocksense-Core[data]"'
        ) from e
    return yf


@dataclass
class YFStockData:
    """
    A class to interact with stock data provided by yfinance api.

    Attributes
    ----------
        ticker : str | list[str]
            Ticker or list of ticker symbol the stock data.
        exchange_market : StockExchangeYahooIdentifier, optional
            Yahoo stock exchange identifier, by default StockExchangeYahooIdentifier.nse
    """

    ticker: str | list[str]
    exchange_market: StockExchangeYahooIdentifier = StockExchangeYahooIdentifier.nse

    def __post_init__(self):
        self._ticker_without_exchange = self._remove_exchange_symbol(self.ticker)
        if isinstance(self.ticker, str):
            # python splits all letters of string & we'll have many keys instead of one
            self._ticker_data = dict.fromkeys([self._ticker_without_exchange])

        if isinstance(self.ticker, list):
            self._ticker_data = dict.fromkeys(self._ticker_without_exchange)

        self._ticker_handler = self._create_ticker_handler()

    @property
    def yahoo_aware_ticker(self) -> str | list[str]:
        return self._add_exchange_symbol(
            self._ticker_without_exchange, self.exchange_market.value
        )

    @property
    def ticker_handler(self) -> "yf.Ticker | yf.Tickers":
        if self._ticker_handler is None:
            self._ticker_handler = self._create_ticker_handler()
        return self._ticker_handler

    def _create_ticker_handler(self) -> "yf.Ticker | yf.Tickers":
        yf = _require_yfinance()
        return (
            yf.Ticker(self.yahoo_aware_ticker)
            if isinstance(self.ticker, str)
            else yf.Tickers(" ".join(self.yahoo_aware_ticker))
        )

    def get_ticker_info(self) -> dict[str, dict]:
        yf = _require_yfinance()
        handler = self.ticker_handler
        if isinstance(handler, yf.Ticker):
            self._ticker_data[self._ticker_without_exchange] = handler.get_info()
        else:
            for ex_tick, tick in zip(
                self.yahoo_aware_ticker, self._ticker_without_exchange
            ):
                self._ticker_data[tick] = handler.tickers[ex_tick].get_info()

        return self._ticker_data

    def get_ticker_history(
        self,
        period: DataPeriod | None = DataPeriod.FIVE_DAYS,
        interval: DataInterval = DataInterval.ONE_DAY,
        start: date | None = None,
        end: date | None = None,
    ) -> dict[str, pl.DataFrame]:
        # If explicit date bounds are provided, period must be disabled for yfinance.
        period = None if start and end else period.value
        handler = self.ticker_handler
        if isinstance(self.ticker, str):
            result = self._history_with_repair_fallback(
                handler,
                period=period,
                interval=interval.value,
                start=start,
                # yfinance treats end as exclusive in some cases, so shift by +1 day.
                end=end + timedelta(days=1) if end else None,
                actions=False,
                raise_errors=True,
                # NOTE - not present in single `Ticker` object
                # progress=False,
                # group_by="ticker",
            )
            self._ticker_data[self._ticker_without_exchange] = (
                self._transform_history_result(result)
            )

        else:
            result = self._history_with_repair_fallback(
                handler,
                period=period,
                interval=interval.value,
                start=start,
                # yfinance treats end as exclusive in some cases, so shift by +1 day.
                end=end + timedelta(days=1) if end else None,
                group_by="ticker",
                actions=False,
                progress=False,
                # raise_errors=True, # NOTE - currently not supported by `Tickers` object
            )
            for ex_tick, tick in zip(
                self.yahoo_aware_ticker, self._ticker_without_exchange
            ):
                self._ticker_data[tick] = self._transform_history_result(
                    result[ex_tick]
                )

        return self._ticker_data

    # TODO - add methods supporting all other api functionality provided by YFinance

    @staticmethod
    def _history_with_repair_fallback(handler, **history_kwargs):
        try:
            # Prefer repaired prices, but retry without repair for current upstream bug paths.
            result = handler.history(**history_kwargs, repair=True)
            if getattr(result, "empty", False):
                logger.warning(
                    "yfinance returned empty result with repair=True. Retrying with repair=False."
                )
                return handler.history(**history_kwargs, repair=False)
            return result
        except ValueError as exc:
            if "output array is read-only" not in str(exc):
                raise
            logger.warning(
                "yfinance repair=True failed with read-only array error. Retrying with repair=False."
            )
            return handler.history(**history_kwargs, repair=False)

    @staticmethod
    def _remove_exchange_symbol(symbol: str | list[str]) -> str | list[str]:
        if isinstance(symbol, str):
            return symbol.split(".")[0]
        else:
            return [i.split(".")[0] for i in symbol]

    @staticmethod
    def _add_exchange_symbol(symbol: str | list[str], exchange) -> str | list[str]:
        if isinstance(symbol, str):
            return symbol + exchange
        else:
            return [i + exchange for i in symbol]

    @staticmethod
    def _transform_history_result(data):
        return (
            pl
            .from_pandas(data, include_index=True)
            # Normalize yfinance index/timestamp naming and schema for downstream strategy code.
            .rename(
                lambda name: "date" if name in ["Date", "Datetime"] else name.lower()
            )
            .drop_nulls()
            .cast({pl.Float64: pl.Float32, "volume": pl.Int64})
            .select("date", "open", "high", "low", "close", "volume")
        )
