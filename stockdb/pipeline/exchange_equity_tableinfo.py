import logging
import os
from datetime import datetime

import polars as pl
from api.models import StockExchange
from rich.progress import track
from rich.prompt import Prompt
from stocksense.config import get_settings
from stocksense.data import Exchange, StockDataDB

logger = logging.getLogger("stockdb")
settings = get_settings(os.getenv("CONFIG_FILE"))
exch = Exchange()


def get_all_tickers(exchange: str) -> list[str]:
    _ = getattr(exch, exchange.lower())
    tickers = _.get_stock_list()
    logger.info(f"Total {exchange} tickers in to download: {len(tickers)}")
    return tickers


def download_nse_equity_table_info(tickers: list[str]) -> pl.LazyFrame:

    data = []
    for ticker in track(tickers, description="Downloading NSE equity data"):
        ticker_info = exch.nse.get_stock_info(ticker)
        # NOTE - Not all tickers may have complete info, so need to handle those cases
        # getting symbol and company name
        info = ticker_info.get("info", None)
        if not info:
            logger.warning(f"Skipping {ticker} as no info found")
            continue

        # Metadata
        metadata = ticker_info.get("metadata", {})
        # Parse Listing Date
        listing_date_str = metadata.get("listingDate", "NA")
        listing_date = None
        if listing_date_str != "NA":
            try:
                listing_date = datetime.strptime(listing_date_str, "%d-%b-%Y").date()
            except (ValueError, TypeError):
                listing_date = None
        # Parse Index Symbol
        raw_index = metadata.get("pdSectorIndAll", "NA")
        if isinstance(raw_index, list):
            index = raw_index
        elif raw_index != "NA":
            index = [raw_index]
        else:
            index = ["No Index"]
        # Parse Series
        series = metadata.get("series", None)

        data.append({
            "symbol": info.get("symbol"),
            "company": info.get("companyName"),
            "index_symbol": index,
            "series": series,
            "listing_date": listing_date,
        })

    return pl.LazyFrame(
        data,
        schema={
            "symbol": pl.String,
            "company": pl.String,
            "index_symbol": pl.List(pl.String),
            "series": pl.String,
            "listing_date": pl.Date,
        },
        strict=False,
    )


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    selected_exch = Prompt.ask(
        "Choose exchange to download",
        choices=StockExchange._member_names_,
        default=StockExchange.nse.value,
        case_sensitive=False,
    ).lower()
    tickers = get_all_tickers(selected_exch)
    match selected_exch:
        case "nse":
            equity_data = download_nse_equity_table_info(tickers)
        case _:
            raise ValueError(f"Unsupported exchange: {selected_exch}")

    equity_table = StockDataDB(
        settings.stockdb.data_base_path / f"{selected_exch}/equity"
    )
    result = equity_table.merge(equity_data.collect(), predicate="s.symbol = t.symbol")
    logger.info(f"Equity data for {selected_exch} downloaded and merged successfully.")
