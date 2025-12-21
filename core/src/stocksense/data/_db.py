from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Final

import deltalake
import duckdb
import polars as pl


@dataclass
class StockDataDB:
    """A class to interact with stock data stored in Delta Lake format."""

    table_name: ClassVar[Final[str]] = "stockdb"

    db_path: Path
    table_version: int | str | datetime | None = None

    def __post_init__(self):
        self._table = pl.scan_delta(
            source=self.db_path,
            version=self.table_version,
        )

    @property
    def table_data(self):
        return self._table

    def sql_filter(self, query: str) -> pl.LazyFrame:
        # NOTE - duckdb needs df variable in local scope to refer as table. Here `self._table` is
        # referred as `stockdb` table locally
        # WARNING - this should match the table_name variable above
        stockdb = self._table  # noqa: F841
        return duckdb.sql(query).pl(lazy=True)

    def polars_filter(self, *predicates: Any, **constraints: Any) -> pl.LazyFrame:
        return self._table.filter(*predicates, **constraints)

    def merge(self, data: pl.DataFrame):
        return (
            data.write_delta(
                target=self.db_path,
                mode="merge",
                delta_merge_options={
                    "writer_properties": deltalake.WriterProperties(
                        compression="ZSTD", compression_level=5
                    ),
                    "source_alias": "s",
                    "target_alias": "t",
                    "predicate": "s.date = t.date AND s.ticker = t.ticker",
                },
            )
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute()
        )
