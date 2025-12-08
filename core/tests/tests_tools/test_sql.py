import pytest
from sqlglot.errors import ParseError
from stocksense.tools.sql import SQLQueryValidator


@pytest.fixture(scope="module")
def sql_queries() -> dict:
    return {
        "valid_query": "SELECT * FROM self WHERE id = 1",
        "invalid_query": "SELEC * FORM self WHERE id = 1",
        "wrong_table_query": "SELECT * FROM not_self WHERE id = 1",
        "join_query": "SELECT a.id, b.value FROM self a JOIN other_table b ON a.id = b.id",
    }


def test_sql_query_validator_syntax_valid(sql_queries: dict):
    validator = SQLQueryValidator(sql_queries["valid_query"])
    assert sql_queries["valid_query"] == (
        validator.verify_syntax().verify_table_name("self").run(optimize=False)
    )

    with pytest.raises(ParseError):
        validator1 = SQLQueryValidator(sql_queries["invalid_query"])
        assert sql_queries["invalid_query"] == (
            validator1.verify_syntax().verify_table_name("self").run(optimize=False)
        )


def test_sql_query_validator_table_name(sql_queries: dict):
    validator = SQLQueryValidator(sql_queries["join_query"])
    assert sql_queries["join_query"] == (
        validator.verify_syntax().verify_table_name("self").run(optimize=False)
    )

    with pytest.raises(ValueError):
        validator1 = SQLQueryValidator(sql_queries["wrong_table_query"])
        assert sql_queries["wrong_table_query"] == (
            validator1.verify_syntax().verify_table_name("self").run(optimize=False)
        )


def test_sql_query_validator_columns(sql_queries: dict):
    validator = SQLQueryValidator(sql_queries["join_query"])
    assert sql_queries["join_query"] == (
        validator.verify_syntax().verify_columns(["id", "value"]).run(optimize=False)
    )

    with pytest.raises(ValueError):
        validator1 = SQLQueryValidator(sql_queries["join_query"])
        assert sql_queries["join_query"] == (
            validator1.verify_syntax()
            .verify_columns(["non_existent_column"])
            .run(optimize=False)
        )
