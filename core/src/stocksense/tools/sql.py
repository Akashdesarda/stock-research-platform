import logging
from dataclasses import dataclass
from typing import Self

from sqlglot import exp, optimizer, parse_one
from sqlglot.dialects.dialect import Dialects, DialectType
from sqlglot.errors import ParseError

logger = logging.getLogger("stocksense")


@dataclass
class SQLQueryValidator:
    """Class to represent a SQL query parser."""

    query: str
    dialect: DialectType = Dialects.DUCKDB

    def run(self, optimize: bool = True) -> str:
        """Run the SQL query validations and return the original query if valid."""
        return (
            optimizer.optimize(self.query, dialect=self.dialect).sql(
                pretty=True, dialect=self.dialect
            )
            if optimize
            else self.query
        )

    def verify_syntax(self) -> Self:
        """Method to verify the syntax of the SQL query."""
        try:
            parse_one(self.query, dialect=self.dialect)
            return self
        except ParseError as e:
            # TODO - use logging instead of print
            logger.error(f"Invalid SQL syntax: {e}")
            raise e

    def verify_table_name(self, table_name: str = "stockdb") -> Self:
        """Method to verify if the SQL query contains the specified table name."""
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
        """Method to verify if the SQL query contains the specified columns."""
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
