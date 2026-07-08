"""Unit tests for optimized SQL validation tools."""

import pytest
import polars as pl
from sqlglot import parse_one
from sqlglot.dialects.dialect import Dialects

from app.skills.tools.sql import (
    _analyze_empty_result,
    _extract_date_filters,
    _extract_ticker_filters,
    _get_table_metadata,
)


class TestTickerExtraction:
    """Test ticker filter extraction from SQL queries."""

    def test_extract_single_ticker_eq(self):
        """Test extracting single ticker from equality filter."""
        query = "SELECT * FROM stockdb WHERE ticker = 'TCS'"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        tickers = _extract_ticker_filters(parsed)
        assert tickers == ["TCS"]

    def test_extract_multiple_tickers_in(self):
        """Test extracting multiple tickers from IN clause."""
        query = "SELECT * FROM stockdb WHERE ticker IN ('TCS', 'INFY', 'WIPRO')"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        tickers = _extract_ticker_filters(parsed)
        assert set(tickers) == {"TCS", "INFY", "WIPRO"}

    def test_extract_lowercase_ticker(self):
        """Test that lowercase tickers are converted to uppercase."""
        query = "SELECT * FROM stockdb WHERE ticker = 'tcs'"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        tickers = _extract_ticker_filters(parsed)
        assert tickers == ["TCS"]

    def test_no_ticker_filter(self):
        """Test query without ticker filter."""
        query = "SELECT * FROM stockdb WHERE date >= '2024-01-01'"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        tickers = _extract_ticker_filters(parsed)
        assert tickers == []


class TestDateExtraction:
    """Test date filter extraction from SQL queries."""

    def test_extract_min_date_gte(self):
        """Test extracting minimum date from >= filter."""
        query = "SELECT * FROM stockdb WHERE date >= '2024-01-01'"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        dates = _extract_date_filters(parsed)
        assert dates.get("min_date") == "2024-01-01"

    def test_extract_max_date_lte(self):
        """Test extracting maximum date from <= filter."""
        query = "SELECT * FROM stockdb WHERE date <= '2024-12-31'"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        dates = _extract_date_filters(parsed)
        assert dates.get("max_date") == "2024-12-31"

    def test_extract_date_range(self):
        """Test extracting both min and max dates."""
        query = "SELECT * FROM stockdb WHERE date >= '2024-01-01' AND date <= '2024-12-31'"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        dates = _extract_date_filters(parsed)
        assert dates.get("min_date") == "2024-01-01"
        assert dates.get("max_date") == "2024-12-31"

    def test_extract_date_between(self):
        """Test extracting date range from BETWEEN clause."""
        query = "SELECT * FROM stockdb WHERE date BETWEEN '2024-01-01' AND '2024-12-31'"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        dates = _extract_date_filters(parsed)
        assert dates.get("min_date") == "2024-01-01"
        assert dates.get("max_date") == "2024-12-31"

    def test_no_date_filter(self):
        """Test query without date filter."""
        query = "SELECT * FROM stockdb WHERE ticker = 'TCS'"
        parsed = parse_one(query, dialect=Dialects.DUCKDB)
        dates = _extract_date_filters(parsed)
        assert dates == {}


class TestEmptyResultAnalysis:
    """Test analysis of queries that return no data."""

    def test_analyze_missing_ticker(self):
        """Test analysis when ticker is not found."""
        query = "SELECT * FROM stockdb WHERE ticker = 'NONEXISTENT'"
        
        # Create metadata
        metadata = {
            "row_count": 1000,
            "date_range": {
                "min_date": "2024-01-01",
                "max_date": "2024-12-31"
            },
            "tickers": ["TCS", "INFY", "WIPRO"]
        }
        
        result = _analyze_empty_result(query, metadata)
        
        assert "NONEXISTENT" in result
        assert "not found" in result.lower()
        assert "3 unique symbols" in result

    def test_analyze_out_of_range_date(self):
        """Test analysis when date is outside available range."""
        query = "SELECT * FROM stockdb WHERE date >= '2025-01-01'"
        
        metadata = {
            "row_count": 1000,
            "date_range": {
                "min_date": "2024-01-01",
                "max_date": "2024-12-31"
            },
            "tickers": ["TCS", "INFY"]
        }
        
        result = _analyze_empty_result(query, metadata)
        
        assert "2025-01-01" in result
        assert "2024-12-31" in result
        assert "Dataset summary" in result

    def test_analyze_includes_dataset_summary(self):
        """Test that analysis always includes dataset summary."""
        query = "SELECT * FROM stockdb WHERE 1=0"  # Always false condition
        
        metadata = {
            "row_count": 5000,
            "date_range": {
                "min_date": "2024-01-01",
                "max_date": "2024-12-31"
            },
            "tickers": ["TCS", "INFY"]
        }
        
        result = _analyze_empty_result(query, metadata)
        
        assert "Dataset summary" in result
        assert "Total rows" in result
        assert "5000" in result or "5,000" in result
        assert "2024-01-01" in result
        assert "2024-12-31" in result


class TestMetadataCaching:
    """Test metadata functionality."""

    def test_metadata_function_exists(self):
        """Test that metadata function is callable."""
        # Verify the function exists and is callable
        assert callable(_get_table_metadata)
        
        # Note: Caching is not currently implemented but could be added in the future
        # using @lru_cache decorator for performance optimization


    def test_missing_ticker_shows_count_not_list(self):
        """Verify that error shows ticker count, not full list."""
        query = "SELECT * FROM stockdb WHERE ticker = 'NONEXISTENT'"
        
        # Large ticker list to simulate real scenario
        metadata = {
            "row_count": 10000,
            "date_range": {
                "min_date": "2024-01-01",
                "max_date": "2024-12-31"
            },
            "tickers": [f"TICKER{i}" for i in range(2000)]  # 2000 tickers
        }
        
        result = _analyze_empty_result(query, metadata)
        
        # Should show count, not list
        assert "2000 unique symbols" in result or "2,000 unique symbols" in result
        
        # Should NOT contain individual ticker symbols (except the missing one)
        assert "TICKER0" not in result
        assert "TICKER1" not in result
        
        # Should show the problematic ticker
        assert "NONEXISTENT" in result

    def test_token_efficiency(self):
        """Verify error message is token-efficient."""
        query = "SELECT * FROM stockdb WHERE ticker = 'MISSING'"
        
        metadata = {
            "row_count": 10000,
            "date_range": {
                "min_date": "2024-01-01",
                "max_date": "2024-12-31"
            },
            "tickers": [f"TICKER{i}" for i in range(2000)]
        }
        
        result = _analyze_empty_result(query, metadata)
        
        # Error message should be concise (< 500 characters for typical case)
        assert len(result) < 500
        
        # Should contain essential information
        assert "MISSING" in result
        assert "not found" in result.lower()
        assert "2000" in result or "2,000" in result


@pytest.mark.integration
class TestIntegration:
    """Integration tests for SQL validation (requires actual data)."""

    @pytest.mark.skip(reason="Requires actual stock data")
    def test_validation_with_real_data(self):
        """Test validation against real stock data."""
        # This would test the full validation pipeline
        # with actual data from the database
        pass

    @pytest.mark.skip(reason="Requires actual stock data")
    def test_performance_improvement(self):
        """Test that sample-based validation is faster than full dataset."""
        # This would measure and compare execution times
        pass
