from datetime import date

import pytest
from api.models import (
    StockExchange,
    StockExchangeYahooIdentifier,
    TaskMode,
    TaskTickerHistoryDownloadInput,
    TickerHistoryDownloadMode,
    YahooTickerIdentifier,
)
from pydantic import ValidationError


@pytest.mark.parametrize(
    "exchange,mode,ticker,start_date,end_date,download_mode,expected_tickers",
    [
        # Happy path: auto mode, no dates, tickers provided
        (
            StockExchange.nse,
            TaskMode.auto,
            ["infy", "tcs", "AKASH"],
            None,
            None,
            TickerHistoryDownloadMode.incremental,
            ["INFY", "TCS", "AKASH"],
        ),
        # Happy path: manual mode, dates provided, tickers provided
        (
            StockExchange.bse,
            TaskMode.manual,
            ["reliance", "hdfc"],
            date(2024, 1, 1),
            date(2024, 2, 1),
            TickerHistoryDownloadMode.full,
            ["RELIANCE", "HDFC"],
        ),
        # Happy path: manual mode, start_date == end_date
        (
            StockExchange.nasdaq,
            TaskMode.manual,
            ["aapl"],
            date(2023, 5, 5),
            date(2023, 5, 5),
            TickerHistoryDownloadMode.incremental,
            ["AAPL"],
        ),
    ],
    ids=[
        "auto_mode_valid_tickers",
        "manual_mode_valid_dates_and_tickers",
        "manual_mode_same_start_end_date",
    ],
)
def test_task_ticker_history_download_input_happy_paths(
    exchange, mode, ticker, start_date, end_date, download_mode, expected_tickers
):
    # Arrange

    # Act
    input_obj = TaskTickerHistoryDownloadInput(
        exchange=exchange,
        task_mode=mode,
        ticker=list(ticker) if ticker is not None else None,
        start_date=start_date,
        end_date=end_date,
        download_mode=download_mode,
    )
    yahoo_tickers = input_obj.get_yahoo_aware_ticker()

    # Assert
    assert [yt.symbol for yt in yahoo_tickers] == expected_tickers
    assert all(isinstance(yt, YahooTickerIdentifier) for yt in yahoo_tickers)
    assert all(yt.exchange == exchange.name for yt in yahoo_tickers)
    assert all(
        yt.exch_id == getattr(StockExchangeYahooIdentifier, exchange.name)
        for yt in yahoo_tickers
    )


@pytest.mark.parametrize(
    "mode,start_date,end_date,expected_error,expected_msg",
    [
        # Error: auto mode with start_date
        (
            TaskMode.auto,
            date(2024, 1, 1),
            None,
            ValidationError,
            "start_date and end_date should not be provided in auto mode",
        ),
        # Error: auto mode with end_date
        (
            TaskMode.auto,
            None,
            date(2024, 2, 1),
            ValidationError,
            "start_date and end_date should not be provided in auto mode",
        ),
        # Error: auto mode with both dates
        (
            TaskMode.auto,
            date(2024, 1, 1),
            date(2024, 2, 1),
            ValidationError,
            "start_date and end_date should not be provided in auto mode",
        ),
        # Error: manual mode, missing start_date
        (
            TaskMode.manual,
            None,
            date(2024, 2, 1),
            ValidationError,
            "start_date and end_date are required in manual mode",
        ),
        # Error: manual mode, missing end_date
        (
            TaskMode.manual,
            date(2024, 1, 1),
            None,
            ValidationError,
            "start_date and end_date are required in manual mode",
        ),
        # Error: manual mode, start_date > end_date
        (
            TaskMode.manual,
            date(2024, 2, 2),
            date(2024, 2, 1),
            ValidationError,
            "start_date must be less than end_date",
        ),
    ],
    ids=[
        "auto_mode_with_start_date",
        "auto_mode_with_end_date",
        "auto_mode_with_both_dates",
        "manual_mode_missing_start_date",
        "manual_mode_missing_end_date",
        "manual_mode_start_date_gt_end_date",
    ],
)
def test_task_ticker_history_download_input_invalid_dates(
    mode, start_date, end_date, expected_error, expected_msg
):
    # Arrange

    # Act & Assert
    with pytest.raises(expected_error) as exc_info:
        TaskTickerHistoryDownloadInput(
            exchange=StockExchange.nse,
            task_mode=mode,
            ticker=["infy"],
            start_date=start_date,
            end_date=end_date,
            download_mode=TickerHistoryDownloadMode.incremental,
        )
    # Assert
    assert expected_msg in str(exc_info.value)


@pytest.mark.parametrize(
    "ticker,expected_error,expected_msg",
    [
        # Error: ticker is None
        (None, ValueError, "Ticker list is None. Cannot get Yahoo aware ticker."),
        # Error: ticker is empty list
        ([], [], None),  # Should not raise, just return empty list
    ],
    ids=[
        "ticker_none_raises",
        "ticker_empty_returns_empty",
    ],
)
def test_get_yahoo_aware_ticker_edge_cases(ticker, expected_error, expected_msg):
    # Arrange
    input_obj = TaskTickerHistoryDownloadInput(
        exchange=StockExchange.nse,
        task_mode=TaskMode.auto,
        ticker=ticker if ticker is not None else None,
        start_date=None,
        end_date=None,
        download_mode=TickerHistoryDownloadMode.incremental,
    )

    # Act & Assert
    if expected_error:
        with pytest.raises(expected_error) as exc_info:
            input_obj.get_yahoo_aware_ticker()
        assert expected_msg in str(exc_info.value)
    else:
        result = input_obj.get_yahoo_aware_ticker()
        assert result == []


@pytest.mark.parametrize(
    "tickers,expected_upper",
    [
        (["infy", "TCS", "Akash"], ["INFY", "TCS", "AKASH"]),
        (["aapl", "msft"], ["AAPL", "MSFT"]),
        (["RELIANCE"], ["RELIANCE"]),
    ],
    ids=[
        "mixed_case_tickers",
        "lower_case_tickers",
        "already_uppercase",
    ],
)
def test_get_yahoo_aware_ticker_uppercase_conversion(tickers, expected_upper):
    # Arrange
    input_obj = TaskTickerHistoryDownloadInput(
        exchange=StockExchange.nse,
        task_mode=TaskMode.auto,
        ticker=list(tickers),
        start_date=None,
        end_date=None,
        download_mode=TickerHistoryDownloadMode.incremental,
    )

    # Act
    result = input_obj.get_yahoo_aware_ticker()

    # Assert
    assert [yt.symbol for yt in result] == expected_upper
