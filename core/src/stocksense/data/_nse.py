from dataclasses import dataclass
from typing import ClassVar

import polars as pl
from nsetools import Nse


@dataclass
class NSEAccessor:
    nse: ClassVar[Nse] = Nse()

    @classmethod
    def get_stock_list(cls) -> list:
        """Fetch the list of stocks from NSE."""
        return cls.nse.get_stock_codes()

    @classmethod
    def get_stock_info(cls, symbol: str) -> dict:
        """Fetch stock information for a given symbol from NSE."""
        return cls.nse.get_quote(symbol, all_data=True)

    @classmethod
    def get_index_list(cls) -> list:
        """Fetch the list of indices from NSE."""
        return cls.nse.get_index_list()

    @classmethod
    def get_index_info(cls, index_name: str) -> dict:
        """Fetch index information for a given index name from NSE."""
        return cls.nse.get_index_quote(index_name)

    @classmethod
    def get_index_quote(cls) -> pl.DataFrame:
        """Fetch quotes for all indices from NSE."""
        return pl.DataFrame(cls.nse.get_all_index_quote())

    @classmethod
    def get_stock_quote_in_index(cls, index_name: str) -> pl.DataFrame:
        """Fetch stock quotes in a given index from NSE."""
        return pl.DataFrame(cls.nse.get_stock_quote_in_index(index_name))
