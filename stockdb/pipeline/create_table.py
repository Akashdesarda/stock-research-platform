import logging

import deltalake
import polars as pl
from api.models import StockExchange
from deltalake.table import DeltaTable
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from stocksense.config import get_settings

logger = logging.getLogger("stockdb")
settings = get_settings()


def create_ticker_history_table(mode: str = "ignore"):
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
            mode=mode,
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
def create_exchange_equity_table(mode: str = "ignore"):
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
            mode=mode,
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


def create_cache_table(mode: str = "ignore"):
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
        mode=mode,
        delta_write_options={
            "writer_properties": deltalake.WriterProperties(
                compression="ZSTD", compression_level=5
            ),
            "schema_mode": "overwrite",
        },
    )
    dt = DeltaTable(settings.stockdb.data_base_path / "common/prompt_cache")
    dt.optimize.z_order(["prompt_hash", "last_modified"])
    logger.info("Finished creating table & z-ordering for prompt cache")


def create_chat_history_table(mode: str = "ignore"):
    chat_history_table = pl.DataFrame(
        schema={
            "session_id": pl.String,  # Unique ID for the conversation session
            "model": pl.String,  # The LLM model used
            "agent": pl.String,  # The AI agent that was handling the request
            "message_json": pl.String,  # The fully serialized Pydantic AI message
            "timestamp": pl.Datetime,  # When the message was created
        }
    )
    logger.info("Creating chat history table")
    chat_history_table.write_delta(
        settings.stockdb.data_base_path / "common/chat_history",
        mode=mode,
        delta_write_options={
            "writer_properties": deltalake.WriterProperties(
                compression="ZSTD", compression_level=5
            ),
            "schema_mode": "overwrite",
        },
    )
    dt = DeltaTable(settings.stockdb.data_base_path / "common/chat_history")

    dt.optimize.z_order(["session_id", "agent"])
    logger.info("Finished creating table & z-ordering for chat history")


def create_registered_data_table(mode: str = "ignore"):
    registered_data_table = pl.DataFrame(
        schema={
            "dataset_id": pl.String,  # Unique ID for the dataset
            "name": pl.String,  # A human readable name for the dataset
            "description": pl.String,  # A brief description about the dataset
            "logical_plan": pl.Struct({
                "exchange": pl.String,
                "ticker": pl.List(pl.String),
                "interval": pl.String,
                "period": pl.String,
                "start_date": pl.Date,
                "end_date": pl.Date,
                "sql_query": pl.String,
            }),  # The logical plan for how to retrieve the data, stored as a struct with all necessary parameters to reconstruct the Polars LazyFrame
            "tags": pl.List(pl.String),  # to categorize and search the dataset
            "last_modified": pl.Datetime,  # When the dataset was registered
        }
    )

    logger.info("Creating registered data table")
    registered_data_table.write_delta(
        settings.stockdb.data_base_path / "common/registered_data",
        mode=mode,
        delta_write_options={
            "writer_properties": deltalake.WriterProperties(
                compression="ZSTD", compression_level=5
            ),
            "schema_mode": "overwrite",
        },
    )
    dt = DeltaTable(settings.stockdb.data_base_path / "common/registered_data")
    dt.optimize.z_order(["dataset_id", "last_modified"])
    logger.info("Finished creating table & z-ordering for registered data")


def _settings_menu(console: Console, current_mode: str) -> str:
    console.print("\n[cyan]Settings[/cyan]")
    console.print(f"1. Table Creation Mode (current: [green]{current_mode}[/green])")
    console.print("   - ignore: ignore if table already present (default)")
    console.print("   - overwrite: overwrite existing table if present with new data")
    console.print("b. Back to main menu")

    choice = Prompt.ask("Select setting to change", choices=["1", "b"], default="b")
    if choice == "1":
        return Prompt.ask(
            "Select mode",
            choices=["ignore", "overwrite"],
            default=current_mode,
        )
    return current_mode


def _display_menu(console: Console, current_mode: str) -> None:
    """Render a small menu of options using Rich Table."""
    table = Table(title=f"Create Tables (Mode: {current_mode})")
    table.add_column("Option", justify="center", style="cyan", no_wrap=True)
    table.add_column("Action", style="magenta")
    table.add_row("1", "Create ticker history table")
    table.add_row("2", "Create exchange equity table")
    table.add_row("3", "Create prompt cache table")
    table.add_row("4", "Create chat history table")
    table.add_row("5", "Create register data table")
    table.add_row("all", "Create all tables")
    table.add_row("s", "Settings (Change mode)")
    table.add_row("q", "Quit")
    console.print(table)


def main() -> None:
    console = Console()
    current_mode = "ignore"

    options = {
        "1": create_ticker_history_table,
        "2": create_exchange_equity_table,
        "3": create_cache_table,
        "4": create_chat_history_table,
        "5": create_registered_data_table,
    }

    while True:
        _display_menu(console, current_mode)
        choice = Prompt.ask(
            "Select an option",
            choices=list(options.keys()) + ["all", "s", "q"],
            default="all",
        )
        if choice == "q":
            console.print("Goodbye!")
            break
        elif choice == "s":
            current_mode = _settings_menu(console, current_mode)
            continue
        elif choice == "all":
            funcs = [
                create_ticker_history_table,
                create_exchange_equity_table,
                create_cache_table,
                create_chat_history_table,
                create_registered_data_table,
            ]
            for func in funcs:
                try:
                    func(current_mode)
                except Exception as exc:
                    console.print(f"[red]Error while running action: {exc}[/red]")
            if Confirm.ask("Run another action?"):
                continue
            else:
                break

        action = options.get(choice)
        if not action:
            console.print(f"[red]Invalid choice: {choice}[/red]")
            continue

        try:
            action(current_mode)
            console.print(f"[green]Completed action for '{choice}'[/green]")
        except Exception as exc:  # pragma: no cover - interactive error handling
            console.print(f"[red]Error while running action '{choice}': {exc}[/red]")

        if not Confirm.ask("Run another action?"):
            break


if __name__ == "__main__":
    main()
