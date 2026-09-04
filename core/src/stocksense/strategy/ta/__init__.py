from collections.abc import Callable
from dataclasses import dataclass

import polars as pl


@dataclass
class BaseAccessor:
    df: pl.LazyFrame
    group_by: str | None = None
    sort_by: str | None = None
    sort_desc: bool = False

    def __post_init__(self):
        if self.sort_by:
            self.df = self.df.sort(self.sort_by, descending=self.sort_desc)
        if self.group_by:
            members = (
                self.df.select(self.group_by)
                .unique()
                .collect()
                .to_series()
                .sort()
            )
            self.df_group = [
                self.df.filter(pl.col(self.group_by) == member)
                for member in members
            ]
        else:
            self.df_group = [self.df]

    def _apply_to_groups(
        self,
        input_cols: list[str] | dict[str, str],
        calculate: Callable[..., list[pl.Series]],
    ) -> pl.LazyFrame:
        result = []

        # creating a mapping dict of param name with its associated actual column name
        if isinstance(input_cols, dict):
            col_map = input_cols
        else:
            col_map = {col: col for col in input_cols}

        for df in self.df_group:
            # param name: actual column name
            inputs = {
                # Collect input columns as numpy arrays
                param_name: df.select(col_name).collect().to_series().to_numpy()
                for param_name, col_name in col_map.items()
            }
            result.append(df.with_columns(calculate(**inputs)))

        return pl.concat(result)
