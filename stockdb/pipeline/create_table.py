import logging
import os

import deltalake
import polars as pl
from api.models import StockExchange
from deltalake.table import DeltaTable
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from stocksense.config import get_settings

logger = logging.getLogger("stockdb")
settings = get_settings(os.getenv("CONFIG_FILE"))


def create_ticker_history_table():
    # SECTION - Create ticker history table
    ticker_history = pl.DataFrame(
        schema={
            "date": pl.Datetime,
            "ticker": pl.String,
            "company": pl.String,
            "open": pl.Float32,
            "high": pl.Float32,
            "low": pl.Float32,
            "close": pl.Float32,
            "volume": pl.Int64,
        }
    )

    # Creating ticker history table for all exchange
    for exchange in StockExchange:
        logger.info(f"Creating ticker history table for {exchange.name}")
        ticker_history.write_delta(
            settings.stockdb.data_base_path / f"{exchange.value}/ticker_history",
            mode="ignore",
            delta_write_options={
                "writer_properties": deltalake.WriterProperties(
                    compression="ZSTD", compression_level=5
                ),
                "schema_mode": "overwrite",
            },
        )
        dt = DeltaTable(
            settings.stockdb.data_base_path / f"{exchange.value}/ticker_history"
        )
        dt.optimize.z_order(["date", "ticker", "company"])
        logger.info(f"Finished creating table & z-ordering for {exchange.name}")


# SECTION - Create equity table
def create_exchange_equity_table():
    ticker_equity = pl.DataFrame(
        schema={
            "symbol": pl.String,
            "company": pl.String,
            "index_symbol": pl.List(pl.String),
            "series": pl.String,
            "listing_date": pl.Date,
        }
    )
    # Creating ticker history table for all exchange
    for exchange in StockExchange:
        logger.info(f"Creating equity table for {exchange.name}")
        ticker_equity.write_delta(
            settings.stockdb.data_base_path / f"{exchange.value}/equity",
            mode="overwrite",
            delta_write_options={
                "writer_properties": deltalake.WriterProperties(
                    compression="ZSTD", compression_level=5
                ),
                "schema_mode": "overwrite",
            },
        )
        dt = DeltaTable(settings.stockdb.data_base_path / f"{exchange.value}/equity")
        dt.optimize.z_order(["symbol", "company", "index_symbol"])
        logger.info(f"Finished creating table & z-ordering for {exchange.name}")


def create_cache_table():
    prompt_cache_table = pl.DataFrame(
        schema={
            "prompt_hash": pl.String,
            "prompt": pl.String,
            "response": pl.String,
            "thinking": pl.String,
            "agent": pl.String,
            "model": pl.String,
            "ttl": pl.Int64,
            "last_modified": pl.Datetime,
        }
    )
    logger.info("Creating prompt cache table")
    prompt_cache_table.write_delta(
        settings.stockdb.data_base_path / "common/prompt_cache",
        mode="ignore",
        delta_write_options={
            "writer_properties": deltalake.WriterProperties(
                compression="ZSTD", compression_level=5
            ),
            # "schema_mode": "overwrite",
        },
    )
    dt = DeltaTable(settings.stockdb.data_base_path / "common/prompt_cache")
    dt.optimize.z_order(["prompt_hash", "last_modified"])
    logger.info("Finished creating table & z-ordering for prompt cache")


def _display_menu(console: Console) -> None:
    """Render a small menu of options using Rich Table."""
    table = Table(title="Create Tables")
    table.add_column("Option", justify="center", style="cyan", no_wrap=True)
    table.add_column("Action", style="magenta")
    table.add_row("1", "Create ticker history table")
    table.add_row("2", "Create exchange equity table")
    table.add_row("3", "Create prompt cache table")
    table.add_row("all", "Create all tables")
    table.add_row("q", "Quit")
    console.print(table)


def main() -> None:
    console = Console()

    options = {
        "1": create_ticker_history_table,
        "2": create_exchange_equity_table,
        "3": create_cache_table,
        "all": lambda: (
            create_ticker_history_table(),
            create_exchange_equity_table(),
            create_cache_table(),
        ),
    }

    while True:
        _display_menu(console)
        choice = Prompt.ask(
            "Select an option", choices=list(options.keys()) + ["q"], default="all"
        )
        if choice == "q":
            console.print("Goodbye!")
            break

        action = options.get(choice)
        if not action:
            console.print(f"[red]Invalid choice: {choice}[/red]")
            continue

        if not Confirm.ask(f"Proceed with '{choice}'?"):
            continue

        try:
            action()
            console.print(f"[green]Completed action for '{choice}'[/green]")
        except Exception as exc:  # pragma: no cover - interactive error handling
            console.print(f"[red]Error while running action '{choice}': {exc}[/red]")

        if not Confirm.ask("Run another action?"):
            break


if __name__ == "__main__":
    main()
