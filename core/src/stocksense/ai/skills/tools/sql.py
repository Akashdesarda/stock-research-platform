import logging
from dataclasses import dataclass
from typing import Self

import duckdb
import polars as pl
from sqlglot import exp, optimizer, parse_one
from sqlglot.dialects.dialect import Dialects, DialectType
from sqlglot.errors import ParseError

logger = logging.getLogger("stocksense")


@dataclass
class SQLQueryValidator:
    """
    Class to represent a SQL query parser.

    Attributes
    ----------
    query : str
        The SQL query string to be validated.
    dialect : DialectType
        The SQL dialect to parse with, defaults to Dialects.DUCKDB.
    """

    query: str
    dialect: DialectType = Dialects.DUCKDB

    def run(self, optimize: bool = True) -> str:
        """
        Run the SQL query validations and return the query string.

        Parameters
        ----------
        optimize : bool, optional
            Whether to optimize the SQL query using the sqlglot optimizer,
            by default True.

        Returns
        -------
        str
            The formatted and optionally optimized SQL query string.
        """
        return (
            optimizer.optimize(self.query, dialect=self.dialect).sql(
                pretty=True, dialect=self.dialect
            )
            if optimize
            else parse_one(self.query, read=self.dialect).sql(
                pretty=True, dialect=self.dialect
            )
        )

    def verify_syntax(self) -> Self:
        """
        Verify the syntax of the SQL query.

        Returns
        -------
        Self
            The current instance for method chaining.

        Raises
        ------
        ParseError
            If the SQL syntax is invalid according to the specified dialect.
        """
        try:
            parse_one(self.query, dialect=self.dialect)
            return self
        except ParseError as e:
            # TODO - use logging instead of print
            logger.error(f"Invalid SQL syntax: {e}")
            raise e

    def verify_table_name(self, table_name: str = "stockdb") -> Self:
        """
        Verify if the SQL query contains the specified table name.

        Parameters
        ----------
        table_name : str, optional
            The table name that must be present in the query, by default "stockdb".

        Returns
        -------
        Self
            The current instance for method chaining.

        Raises
        ------
        ValueError
            If the specified table name is not found in the parsed query tables.
        ParseError
            If the SQL syntax is invalid.
        """
        try:
            # Parse the SQL query
            expression = parse_one(self.query, dialect=self.dialect)

            # Find all 'exp.Table' nodes in the AST
            table_expressions = expression.find_all(exp.Table)

            # Extract the table name
            table_names = {table.this.name for table in table_expressions}

            if table_name in table_names:
                return self
            else:
                raise ValueError(
                    f"Table name '{table_name}' not found in query. Found tables: {table_names}"
                )

        except ParseError as e:
            logger.error(f"Invalid SQL syntax: {e}")
            raise e

    def verify_columns(self, required_columns: list[str]) -> Self:
        """
        Verify if the SQL query contains the specified columns.

        Parameters
        ----------
        required_columns : list[str]
            A list of column names that must be present in the query.

        Returns
        -------
        Self
            The current instance for method chaining.

        Raises
        ------
        ValueError
            If any of the required columns are missing from the parsed query.
        ParseError
            If the SQL syntax is invalid.
        """
        # FIXME - The columns name provided as input param are too hardcoded and rigid. In case
        # where the resultant query will have a new calculated column then current logic won't work

        try:
            # Parse the SQL query
            expression = parse_one(self.query, dialect=self.dialect)

            # Find all 'exp.Column' nodes in the AST
            column_expressions = expression.find_all(exp.Column)

            # Extract the column names
            column_names = {column.name for column in column_expressions}

            if missing_columns := [
                col for col in required_columns if col not in column_names
            ]:
                raise ValueError(
                    f"Missing required columns in query: {missing_columns}. Found columns: {column_names}"
                )

            else:
                return self
        except ParseError as e:
            logger.error(f"Invalid SQL syntax: {e}")
            raise e

    # TODO - add more validation methods as needed


def check_sql_query_returns_data(data: pl.LazyFrame, query: str) -> bool:
    """Check if the SQL query returns an empty dataset

    Parameters
    ----------
    data : pl.LazyFrame
        The Polars LazyFrame representing the query plan or dataset.
    query : str
        The SQL query string to be executed against the registered table.

    Returns
    -------
    bool
        True if the query result is not empty, False otherwise.
    """
    # Parse the query and find all table names
    expression = parse_one(query, dialect="duckdb")
    table_names = {table.this.name for table in expression.find_all(exp.Table)}

    # Register the same dataframe for every table name found in the query
    for table_name in table_names:
        duckdb.register(table_name, data)

    # Also register the default just in case
    duckdb.register("stockdb", data)

    result = duckdb.sql(query).pl(lazy=True)
    # inverting the logic because we want to return True if the query returns data
    return not result.limit(1).collect().is_empty()
