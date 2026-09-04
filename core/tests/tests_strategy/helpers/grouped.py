from datetime import date, timedelta
from typing import Any

import polars as pl

from stocksense.strategy import TechnicalAnalysis

ACCESSOR_NAMES = {
    "cycle",
    "momentum",
    "overlap",
    "pattern",
    "stats",
    "trend",
    "volatility",
    "volume",
}


def make_multi_ticker_data(row_count: int = 60) -> pl.DataFrame:
    rows = []
    start = date(2024, 1, 1)

    for idx in range(row_count):
        rows.append(
            {
                "date": start + timedelta(days=idx),
                "ticker": "AAA",
                "open": 100 + idx,
                "high": 102 + idx,
                "low": 98 + idx,
                "close": 101 + idx,
                "volume": 1000 + idx * 10,
                "adjusted_close": 101.5 + idx,
            }
        )
        rows.append(
            {
                "date": start + timedelta(days=idx),
                "ticker": "BBB",
                "open": 200 + idx * 2,
                "high": 203 + idx * 2,
                "low": 197 + idx * 2,
                "close": 201 + idx * 2,
                "volume": 2000 + idx * 20,
                "adjusted_close": 201.5 + idx * 2,
            }
        )

    return pl.DataFrame(rows)


def normalize_talib_output(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.selectors.float().fill_nan(None))


def assert_grouped_matches_single_ticker(
    data: pl.DataFrame,
    accessor_name: str,
    method_name: str,
    output_cols: list[str],
    ticker: str = "BBB",
    **kwargs: Any,
) -> None:
    if accessor_name not in ACCESSOR_NAMES:
        raise ValueError(f"Unsupported accessor: {accessor_name}")

    grouped_accessor = getattr(
        TechnicalAnalysis(data, group_by="ticker", sort_by="date"),
        accessor_name,
    )
    single_accessor = getattr(
        TechnicalAnalysis(
            data.filter(pl.col("ticker") == ticker),
            sort_by="date",
        ),
        accessor_name,
    )

    grouped_result = getattr(grouped_accessor, method_name)(**kwargs).collect()
    grouped = grouped_result.filter(pl.col("ticker") == ticker).select(
        output_cols
    )
    single = (
        getattr(single_accessor, method_name)(**kwargs)
        .collect()
        .select(output_cols)
    )

    assert grouped_result.height == data.height
    assert set(grouped_result["ticker"].unique()) == set(
        data["ticker"].unique()
    )
    assert (
        normalize_talib_output(grouped).to_dicts()
        == normalize_talib_output(single).to_dicts()
    )
