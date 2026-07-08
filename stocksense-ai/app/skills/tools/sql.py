import logging

import duckdb
import polars as pl
from agno.exceptions import RetryAgentRun
from agno.run import RunContext
from sqlglot import exp, parse_one
from sqlglot.dialects.dialect import Dialects
from sqlglot.errors import ParseError
from stocksense.config import get_settings
from stocksense.data import StockDataDB

logger = logging.getLogger("stocksense")
settings = get_settings()


def verify_duckdb_sql_query_syntax(query: str) -> str:
    """You must use this tool to verify the syntax of the DuckDB SQL query.

    Args:
        query (str): The DuckDB SQL query to validate.

    Returns:
        str: A message confirming the query syntax is valid.
    """
    try:
        logger.debug(f"Validating SQL query: {query}")
        parse_one(query, dialect=Dialects.DUCKDB)
        return "Valid SQL query syntax"

    except ParseError as e:
        logger.error(f"Invalid SQL syntax: {e}")
        raise RetryAgentRun(f"Invalid SQL query: {e}") from e


def verify_table_name(query: str, table_name: str = "stockdb") -> str:
    """Use this tool to verify if the given SQL query contains the specified table name.

    Args:
        query (str): The SQL query to be verified.
        table_name (str, optional): The table name that must be present in the query, by default "stockdb".

    Returns:
        str: A message confirming the given table name is used in the query.
    """
    logger.debug(f"Checking if table name '{table_name}' is used in query: {query}")
    try:
        # Parse the SQL query
        expression = parse_one(query, dialect=Dialects.DUCKDB)

        # Find all 'exp.Table' nodes in the AST
        table_expressions = expression.find_all(exp.Table)

        # Extract the table name
        table_names = {table.this.name for table in table_expressions}

        if table_name in table_names:
            return "Correct table name is used in the query."
        logger.error(f"Table name '{table_name}' not found in query.")
        raise RetryAgentRun(
            f"Table name '{table_name}' not found in query. Instead found: {table_names}"
        )

    except ParseError as e:
        logger.error(f"Invalid SQL syntax: {e}")
        raise RetryAgentRun(f"Invalid SQL query: {e}") from e


def verify_sql_query_returns_data(query: str, run_context: RunContext) -> str:
    """Verify if the SQL query returns data by executing it against a sample dataset.

    Note: Use this tool AFTER verifying syntax and table names. If this tool fails, read the error
    message carefully - it can contain useful guidance on what to fix.

    Args:
        query (str): The SQL query string to be executed against the registered table.
        run_context: The run context containing dependencies (automatically provided)

    Returns:
        str: A message confirming the query result is not empty or indicating no data.
    """
    logger.debug(f"Checking if SQL query returns data: {query}")
    try:
        dependencies = run_context.dependencies or {}
        # REVIEW - using NSE as default exchange for now
        exchange = dependencies.get("exchange", "nse")
        table_path = settings.stockdb.data_base_path / f"{exchange}/ticker_history"
        history_table = StockDataDB(table_path)

        # Use duckdb for sql query validation
        logger.debug("Validating sql query if it returns any data using duckdb")
        if history_table.sql_filter(query).limit(1).collect().is_empty():
            # get metadata for detailed error messages
            metadata = _get_table_metadata(history_table.table_data)
            # Analyze why the query returned no data
            error_context = _analyze_empty_result(query, metadata)
            raise RetryAgentRun(
                f"The SQL query is syntactically correct but returns no data. Modify it.\n\n{error_context}"
            )

        return "The SQL query returns data successfully"

    except (duckdb.Error, ParseError) as e:
        logger.warning(f"Error executing SQL query: {e}", exc_info=True)
        raise RetryAgentRun(f"Error executing SQL query: {e}") from e


def _get_table_metadata(history_data: pl.LazyFrame) -> dict:
    logger.debug("Loading metadata for ticker history data")

    # Get metadata without loading full dataset
    metadata = {
        "row_count": history_data.select(pl.len()).collect()[0, 0],
        "date_range": history_data
        .select(
            pl.col("date").min().cast(pl.Date).alias("min_date"),
            pl.col("date").max().cast(pl.Date).alias("max_date"),
        )
        .collect()
        .to_dicts()[0],
        "columns": history_data.collect_schema().names(),
        "tickers": history_data
        .select(pl.col("ticker"))
        .unique()
        .collect()
        .to_series()
        .to_list(),
    }

    logger.debug(
        f"Metadata loaded: {metadata['row_count']:,} rows, "
        f"date range: {metadata['date_range']['min_date']} to {metadata['date_range']['max_date']}"
    )

    return metadata


def _extract_ticker_filters(parsed_query: exp.Expr) -> list[str]:
    """Extract ticker values from WHERE clause filters.

    Args:
        parsed_query: Parsed SQL expression

    Returns:
        list[str]: List of ticker values found in filters
    """
    tickers = []

    # Find all equality comparisons
    for eq in parsed_query.find_all(exp.EQ):
        # Check if one side is a ticker column
        left = eq.left
        right = eq.right

        if isinstance(left, exp.Column) and left.name.lower() == "ticker":
            if isinstance(right, exp.Literal):
                tickers.append(right.this.upper())
        elif isinstance(right, exp.Column) and right.name.lower() == "ticker":
            if isinstance(left, exp.Literal):
                tickers.append(left.this.upper())

    # Find IN clauses with ticker
    for in_expr in parsed_query.find_all(exp.In):
        if (
            isinstance(in_expr.this, exp.Column)
            and in_expr.this.name.lower() == "ticker"
        ):
            tickers.extend(
                item.this.upper()
                for item in in_expr.expressions
                if isinstance(item, exp.Literal)
            )
    return tickers


def _extract_date_filters(parsed_query: exp.Expr) -> dict:
    date_info = {}

    # Find date comparisons
    for comparison in parsed_query.find_all(exp.GTE, exp.GT, exp.LTE, exp.LT, exp.EQ):
        left = comparison.left
        right = comparison.right

        if isinstance(left, exp.Column) and left.name.lower() == "date":
            if isinstance(right, exp.Literal):
                date_value = right.this
                if isinstance(comparison, (exp.GTE, exp.GT)):
                    date_info["min_date"] = date_value
                elif isinstance(comparison, (exp.LTE, exp.LT)):
                    date_info["max_date"] = date_value

        elif isinstance(right, exp.Column) and right.name.lower() == "date":
            if isinstance(left, exp.Literal):
                date_value = left.this
                if isinstance(comparison, (exp.LTE, exp.LT)):
                    date_info["min_date"] = date_value
                elif isinstance(comparison, (exp.GTE, exp.GT)):
                    date_info["max_date"] = date_value

    # Find date BETWEEN ranges
    for between in parsed_query.find_all(exp.Between):
        if isinstance(between.this, exp.Column) and between.this.name.lower() == "date":
            low = between.args.get("low")
            high = between.args.get("high")
            if isinstance(low, exp.Literal):
                date_info["min_date"] = low.this
            if isinstance(high, exp.Literal):
                date_info["max_date"] = high.this

    return date_info


def _analyze_empty_result(query: str, metadata: dict) -> str:
    """Analyze why a query returned no data and provide actionable feedback.

    Args:
        query: The SQL query that returned no data
        metadata: Table metadata including available tickers and date range

    Returns:
        str: Detailed error message with context and suggestions
    """
    try:
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        issues = []
        suggestions = []

        # Check for ticker filters
        ticker_filters = _extract_ticker_filters(parsed)
        if ticker_filters:
            available_tickers = set(metadata["tickers"])
            if missing_tickers := [
                t for t in ticker_filters if t not in available_tickers
            ]:
                issues.append(
                    f"Ticker(s) not found in dataset: {', '.join(missing_tickers)}"
                )

        # Check for date range filters
        date_filters = _extract_date_filters(parsed)
        if date_filters:
            min_date = metadata["date_range"]["min_date"]
            max_date = metadata["date_range"]["max_date"]

            if "min_date" in date_filters and date_filters["min_date"] > str(max_date):
                issues.append(
                    f"Query filters for dates after {date_filters['min_date']}, but latest data is {max_date}"
                )
                suggestions.append(
                    f"Try using a date range within {min_date} to {max_date}"
                )

            if "max_date" in date_filters and date_filters["max_date"] < str(min_date):
                issues.append(
                    f"Query filters for dates before {date_filters['max_date']}, but earliest data is {min_date}"
                )
                suggestions.append(
                    f"Try using a date range within {min_date} to {max_date}"
                )

        # Build error message
        error_parts = []

        if issues:
            error_parts.append("Issues detected:")
            error_parts.extend(f"  - {issue}" for issue in issues)

        error_parts.extend((
            "\nDataset summary:",
            f"  - Total rows: ~{metadata['row_count']}",
            f"  - Date range: {metadata['date_range']['min_date']} to {metadata['date_range']['max_date']}",
            f"  - Available tickers: {len(metadata['tickers'])} unique symbols",
        ))
        # Adding suggestions to the error message if any are available for LLM
        if suggestions:
            error_parts.append("\nSuggestions:")
            error_parts.extend(f"  - {suggestion}" for suggestion in suggestions)

        return "\n".join(error_parts)

    except Exception as e:
        logger.warning(f"Error analyzing empty result: {e}", exc_info=True)
        return "Query returned no data. Please check your filters and try again."
