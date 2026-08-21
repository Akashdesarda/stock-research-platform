import csv
import io
from dataclasses import dataclass
from datetime import date, timedelta
from typing import ClassVar

import polars as pl
from jugaad_data.nse import NSELive, bhavcopy_raw


@dataclass
class NSEAccessor:
    _client: ClassVar[NSELive | None] = None

    @classmethod
    def _nse(cls) -> NSELive:
        """Lazily create the NSELive client (its constructor makes a live
        network call to seed session cookies, so it must not run at import
        time)."""
        if cls._client is None:
            cls._client = NSELive()
        return cls._client

    @classmethod
    def get_stock_list(cls) -> list:
        """Fetch the list of stocks from NSE."""
        for days_back in range(7):
            try:
                raw = bhavcopy_raw(date.today() - timedelta(days=days_back))
            except Exception:
                continue
            symbols = {
                row["TckrSymb"]
                for row in csv.DictReader(io.StringIO(raw))
                if row.get("SctySrs") == "EQ"
            }
            if symbols:
                return sorted(symbols)
        raise RuntimeError("Unable to fetch NSE equity list from bhavcopy")

    @classmethod
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
