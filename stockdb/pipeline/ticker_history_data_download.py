import asyncio
import logging
import os
from datetime import date, timedelta

import polars as pl
from api.models import StockExchange
from rich.progress import track
from rich.prompt import Prompt
from stocksense.config import get_settings
from stocksense.data import (
    Interval,
    Period,
    StockDataDB,
    StockExchangeYahooIdentifier,
    YFStockData,
)

logger = logging.getLogger("stockdb")
settings = get_settings(os.getenv("CONFIG_FILE"))


def calculate_batches(n: int, batch_size: int) -> int:
    """
    Returns the total number of batches required to process 'n' items
    with each batch containing up to 'batch_size' items.
    """
    if batch_size <= 0:
        raise ValueError("Batch size must be greater than zero.")

    return (n + batch_size - 1) // batch_size


def prepare_ticker_history_table(symbol: str, df: pl.DataFrame) -> pl.LazyFrame:
    if not df.is_empty():
        return (
            df
            .lazy()  # converting to lazyframe
            .with_columns(
                # creating primary key
                # key=pl.lit(symbol.lower())
                # + pl.col("date").dt.date().cast(pl.String).str.replace_all("-", ""),
                ticker=pl.lit(symbol.upper()),
            )
            # dropping all null values
            .drop_nulls()
            # .select("date", "key", "ticker", "open", "high", "low", "close", "volume")
        )
    logger.warning(
        f"got empty dataframe, may not able to download {symbol} data from yahoo"
    )
    # passing empty lazyframe, which won't be considered while using pl.concat() in downstream
    return pl.LazyFrame(
        schema={
            "date": pl.Datetime("ns"),
            "open": pl.Float32,
            "high": pl.Float32,
            "low": pl.Float32,
            "close": pl.Float32,
            "volume": pl.Int64,
            "ticker": pl.String,
        }
    )


def download_specific_date_ticker_history(
    exchange: StockExchange, ticker: list[str], last_run_date: date
) -> pl.LazyFrame:
    today = date.today()
    start_date = last_run_date + timedelta(days=1)
    logger.debug(f"downloading from {start_date} to {today}")

    yf = YFStockData(
        ticker=ticker,
        exchange_market=getattr(StockExchangeYahooIdentifier, exchange.value),
    )
    result = yf.get_ticker_history(
        start=start_date, end=today, interval=Interval.ONE_DAY
    )

    return (
        pl
        .concat(
            [prepare_ticker_history_table(symbol, result[symbol]) for symbol in result],
            how="vertical",
        )
        .drop_nulls()
        .join(
            other=pl.scan_delta(
                settings.stockdb.data_base_path / f"{exchange.value}/equity"
            ).rename({"symbol": "ticker"}),
            on="ticker",
            how="left",
        )
        .select("date", "ticker", "company", "open", "high", "low", "close", "volume")
    )


def download_entire_ticker_history(
    exchange: StockExchange, ticker: list[str]
) -> pl.LazyFrame:
    yf = YFStockData(
        ticker=ticker,
        exchange_market=getattr(StockExchangeYahooIdentifier, exchange.value),
    )
    logger.debug("downloading entire historical data")
    result = yf.get_ticker_history(period=Period.MAX, interval=Interval.ONE_DAY)

    return (
        pl
        .concat(
            [prepare_ticker_history_table(symbol, result[symbol]) for symbol in result],
            how="vertical",
        )
        .drop_nulls()
        .join(
            other=pl.scan_delta(
                settings.stockdb.data_base_path / f"{exchange.value}/equity"
            ).rename({"symbol": "ticker"}),
            on="ticker",
            how="left",
        )
        .select("date", "ticker", "company", "open", "high", "low", "close", "volume")
    )


async def download_ticker_history(
    exchange: StockExchange,
) -> dict:
    batch_size = settings.stockdb.download_batch_size
    tickers = (
        await pl
        .scan_delta(settings.stockdb.data_base_path / f"{exchange.value}/equity")
        .select(pl.col("symbol").alias("ticker"))
        .collect_async()
    )
    ticker_length = tickers.count()
    ticker_history_table = StockDataDB(
        settings.stockdb.data_base_path / f"{exchange.value}/ticker_history"
    )
    logger.debug(f"total tickers: {ticker_length}")

    # getting latest date to run the insert job
    logger.info("getting last inserted date")

    latest_date_df = (
        await ticker_history_table.table_data
        .select(pl.col("date").max())  # to get latest available date
        # NOTE - polars return null row if no date found, which makes `is_empty()` `False`
        .filter(~pl.col("date").is_null())
        .collect_async()
    )

    # Determining mode to run from - 'max' or 'last run date'
    if latest_date_df.is_empty():
        use_max = True
        logger.info(f"no data found for {exchange}, running for max date")
    else:
        use_max = False
        logger.info(f"last inserted date was: {latest_date_df.item()}")

    # running batch job
    batched_data = []
    no_of_batches = calculate_batches(ticker_length.item(), batch_size=batch_size)
    for batch in track(
        range(no_of_batches),
        description="Downloading ticker history data",
        total=no_of_batches,
    ):
        current_tickers = (
            tickers
            .slice(batch * batch_size, batch_size)
            .select("ticker")
            .to_series()
            .to_list()
        )
        logger.debug(f"current tickers: \n{current_tickers}")
        if use_max:
            batched_data.append(
                download_entire_ticker_history(exchange, current_tickers)
            )
        else:
            batched_data.append(
                download_specific_date_ticker_history(
                    exchange,
                    current_tickers,
                    latest_date_df.select("date").item(0, 0),
                )
            )

    complete_ticker_history_data = pl.concat(batched_data, how="vertical")
    logger.info("downloading complete of ticker history data")

    # merging data into respective deltalake table
    result = ticker_history_table.merge(
        await complete_ticker_history_data.collect_async()
    )
    logger.info(
        f"successfully merged data into {ticker_history_table.db_path} with following result: {result}"
    )
    return result


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    selected_exc = Prompt.ask(
        "Choose exchange to download",
        choices=StockExchange._member_names_,
        default=StockExchange.nse.value,
        case_sensitive=False,
    ).lower()

    asyncio.run(download_ticker_history(getattr(StockExchange, selected_exc)))
