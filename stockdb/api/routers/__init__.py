import json
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

import polars as pl
from openinference.instrumentation import using_session
from openinference.semconv.trace import SpanAttributes
from opentelemetry import trace
from stocksense.config import get_settings
from stocksense.data import StockDataDB
from stocksense.types import DataInterval, DataPeriod

from api.models import LogicalPlan

settings = get_settings()


def _build_history_lf_from_query(
    data: StockDataDB,
    ticker: list[str],
    start_date: date | None,
    end_date: date | None,
    period: DataPeriod | None,
    interval: DataInterval,
) -> pl.LazyFrame:
    """Helper function to build lazyframe for ticker history data based on query parameters"""
    # getting all the tickers as upper case
    tickers = [t.upper() for t in ticker]

    # Building the query
    # 1. ticker condition
    query = [pl.col("ticker").is_in(tickers)]
    # 2. start & end condition
    if start_date is not None:
        query.append(pl.col("date").is_between(start_date, end_date))
    # 3. Period condition
    elif period:
        query.append(
            pl.col("date")
            >= (
                pl.col("date").min()
                if period == DataPeriod.MAX
                else pl.datetime(datetime.now().year, 1, 1)
                if period == DataPeriod.YEAR_TO_DATE
                else pl.col("date").max().dt.offset_by(f"-{period.value}")
            )
        )
    result = data.polars_filter(query)
    # 4. Interval condition
    if interval not in {
        DataInterval.ONE_DAY,
        DataInterval.FIVE_DAYS,
        DataInterval.ONE_WEEK,
        DataInterval.ONE_MONTH,
        DataInterval.THREE_MONTHS,
    }:
        raise ValueError("Interval less than 1 day is not supported")

    # NOTE - Normalize interval value for '1w'/'1wk'
    interval_value = interval.value
    if interval_value == "1wk":
        interval_value = "1w"

    return (
        result.sort([
            "ticker",
            "date",
        ])  # dynamic grouping requires ascending data within each ticker
        .group_by_dynamic(
            index_column="date",
            group_by="ticker",
            every=interval_value,
            start_by="datapoint",  # grouping should start from first data point
            # aggregation is done by simply taking all value from group; then taking first value from each
        )
        .agg(pl.all().first())
        .select(
            "date",
            "ticker",
            "company",
            "open",
            "high",
            "low",
            "close",
            "volume",
        )
        .sort("date", descending=True)  # sorting back to latest date first
    )


def _logical_plan_to_lf(plan: LogicalPlan) -> pl.LazyFrame:
    """Hydrate & return registered data based on the logical plan provided in the request body"""
    sdb = StockDataDB(
        settings.stockdb.data_base_path / f"{plan.exchange.value}/ticker_history"
    )
    # 1st priority to sql query
    if plan.sql_query:
        return sdb.sql_filter(plan.sql_query)
    # 2nd priority to logical plan serialized in bytes
    else:
        return _build_history_lf_from_query(
            data=sdb,
            ticker=plan.ticker,  # type: ignore
            start_date=plan.start_date,
            end_date=plan.end_date,
            period=plan.period,
            interval=plan.interval,  # type: ignore
        )


__all__ = [
    "_build_history_lf_from_query",
    "_logical_plan_to_lf",
]
