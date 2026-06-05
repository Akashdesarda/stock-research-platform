import logging

import duckdb
from stocksense.config import get_settings
from stocksense.data import StockDataDB
import polars as pl
from agno.exceptions import RetryAgentRun
from agno.run import RunContext
from sqlglot import exp, parse_one
from sqlglot.dialects.dialect import Dialects
from sqlglot.errors import ParseError

logger = logging.getLogger("stocksense")
settings = get_settings()
# TODO - add more validation methods as needed


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
        raise RetryAgentRun(f"Invalid SQL query: {e}")


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
            return "Table name is used in the query."
        else:
            logger.error(f"Table name '{table_name}' not found in query.")
            raise RetryAgentRun(
                f"Table name '{table_name}' not found in query. Found tables: {table_names}"
            )

    except ParseError as e:
        logger.error(f"Invalid SQL syntax: {e}")
        raise RetryAgentRun(f"Invalid SQL query: {e}")


def verify_columns(query: str, required_columns: list[str]) -> str:
    """Use this tool to verify if the SQL query contains the specified columns.

    Args:
        query (str): The SQL query to be verified.
        required_columns (list[str]): A list of column names that must be present in the query.

    Returns:
        str: A message confirming the required columns are present in the query.
    """
    # FIXME - The columns name provided as input param are too hardcoded and rigid. In case
    # where the resultant query will have a new calculated column then current logic won't work
    logger.debug(f"Checking if required columns are present in query: {query}")
    try:
        # Parse the SQL query
        expression = parse_one(query, dialect=Dialects.DUCKDB)

        # Find all 'exp.Column' nodes in the AST
        column_expressions = expression.find_all(exp.Column)

        # Extract the column names
        column_names = {column.name for column in column_expressions}

        if missing_columns := [
            col for col in required_columns if col not in column_names
        ]:
            raise RetryAgentRun(
                f"Missing required columns in query: {missing_columns}. Found columns: {column_names}"
            )
        else:
            return "All required columns are present in the query."
    except ParseError as e:
        logger.error(f"Invalid SQL syntax: {e}")
        raise RetryAgentRun(f"Invalid SQL query: {e}")


def verify_sql_query_returns_data(query: str, run_context: RunContext) -> str:
    """You must use this tool to verify if the SQL query returns any data or empty/no data

    Args:
        query (str): The SQL query string to be executed against the registered table.
        run_context: The run context containing dependencies (automatically provided)

    Returns:
        str: A message confirming the query result is not empty or indicating no data.
    """
    logger.debug(f"Checking if SQL query returns data: {query}")
    try:
        dependencies = run_context.dependencies or {}
        # NOTE - using NSE as default exchange for now
        exchange = dependencies.get("exchange", "nse")
        history_data = StockDataDB(
            settings.stockdb.data_base_path / f"{exchange}/ticker_history"
        )
        if not _check_sql_query_returns_data(history_data.table_data.collect(), query):
            raise RetryAgentRun(
                "The SQL query is valid but returns no data. Please modify the query to return some data."
            )
        return "The SQL query returns data"
    except (duckdb.Error, ParseError) as e:
        logger.warning(f"Error executing SQL query: {e}", exc_info=True)
        raise RetryAgentRun(f"Error executing SQL query: {e}")


def _check_sql_query_returns_data(data: pl.DataFrame, query: str) -> bool:
    # Parse the query and find all table names
    expression = parse_one(query, dialect=Dialects.DUCKDB)
    table_names = {table.this.name for table in expression.find_all(exp.Table)}

    with duckdb.connect() as con:
        # Register the same dataframe for every table name found in the query
        for table_name in table_names:
            con.register(table_name, data)

        # Also register the default just in case
        con.register("stockdb", data)

        result = con.sql(query).pl(lazy=True)
        # inverting the logic because we want to return True if the query returns data
        return not result.limit(1).collect().is_empty()
