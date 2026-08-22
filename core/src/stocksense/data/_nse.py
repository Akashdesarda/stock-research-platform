import csv
import functools
import io
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import ClassVar

import polars as pl
import requests
from jugaad_data.nse import NSELive, bhavcopy_raw
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger("stocksense")

_REQUEST_TIMEOUT_SECONDS = 15


def _reset_nse_client(retry_state) -> None:
    """Drop the cached NSELive client so the next attempt gets a fresh
    session (new cookies). Retrying on the same session is pointless once
    NSE has throttled it."""
    symbol = (
        retry_state.args[1]
        if len(retry_state.args) > 1
        else retry_state.kwargs.get("symbol")
    )
    logger.warning(
        f"NSE request for {symbol!r} failed (attempt {retry_state.attempt_number}): "
        f"{retry_state.outcome.exception()!r} - resetting session before retry"
    )
    NSEAccessor._client = None


@dataclass
class NSEAccessor:
    _client: ClassVar[NSELive | None] = None

    @classmethod
    def _nse(cls) -> NSELive:
        """Lazily create the NSELive client (its constructor makes a live
        network call to seed session cookies, so it must not run at import
        time)."""
        if cls._client is None:
            client = NSELive()
            # NSELive never passes timeout= to its requests.Session, so a
            # throttled/stalled NSE connection hangs forever. Enforce one here.
            client.s.request = functools.partial(
                client.s.request, timeout=_REQUEST_TIMEOUT_SECONDS
            )
            cls._client = client
        return cls._client

    @classmethod
    def get_stock_list(cls) -> list:
        """Fetch the list of stocks from NSE."""
        for days_back in range(7):
            try:
                raw = bhavcopy_raw(date.today() - timedelta(days=days_back))
            except Exception:
                logger.warning(
                    f"Failed to fetch NSE equity list from bhavcopy for {date.today() - timedelta(days=days_back)}"
                )
                continue
            if symbols := {
                row["TckrSymb"]
                for row in csv.DictReader(io.StringIO(raw))
                if row.get("SctySrs") == "EQ"
            }:
                return sorted(symbols)
        raise RuntimeError("Unable to fetch NSE equity list from bhavcopy")

    @classmethod
    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        wait=wait_exponential_jitter(initial=2, max=30),
        stop=stop_after_attempt(4),
        before_sleep=_reset_nse_client,
        reraise=True,
    )
    def get_stock_info(cls, symbol: str) -> dict:
        """Fetch stock information for a given symbol from NSE."""
        quote = cls._nse().stock_quote(symbol)
        meta = quote["metaData"]
        sec = quote["secInfo"]

        return {
            "info": {
                "symbol": meta["symbol"],
                "companyName": meta["companyName"],
            },
            "metadata": {
                "listingDate": sec["listingDate"].split(" ")[0],
                "pdSectorIndAll": sec["indexList"],
                "series": meta["series"],
            },
            "priceInfo": quote["priceInfo"],
            "industryInfo": {
                "macro": sec["macro"],
                "sector": sec["sector"],
                "industry": sec["industryInfo"],
            },
        }

    @classmethod
    def get_index_list(cls) -> list:
        """Fetch the list of indices from NSE."""
        return [record["indexSymbol"] for record in cls._nse().all_indices()["data"]]

    @classmethod
    def get_index_info(cls, index_name: str) -> dict:
        """Fetch index information for a given index name from NSE."""
        data = cls._nse().live_index(index_name)["data"]
        if not data:
            raise ValueError(f"No index found for {index_name!r}")

        record = data[0]
        return {**record, "index": record["symbol"]}

    @classmethod
    def get_index_quote(cls) -> pl.DataFrame:
        """Fetch quotes for all indices from NSE."""
        return pl.DataFrame(cls._nse().all_indices()["data"])

    @classmethod
    def get_stock_quote_in_index(cls, index_name: str) -> pl.DataFrame:
        """Fetch stock quotes in a given index from NSE."""
        return pl.DataFrame(cls._nse().live_index(index_name)["data"])
