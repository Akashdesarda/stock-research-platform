from collections.abc import Callable
from dataclasses import dataclass

import polars as pl


@dataclass
class BaseAccessor:
    df: pl.DataFrame
    group_by: str | None = None

    def __post_init__(self):

        if self.group_by:
            self.df_group = self.df.partition_by(self.group_by)
        else:
            self.df_group = [self.df]

    def _apply_to_groups(
        self,
        input_cols: list[str] | dict[str, str],
        calculate: Callable[..., list[pl.Series]],
    ) -> pl.DataFrame:
        result = []

        # creating a mapping dict of param name with its associated actual column name
        if isinstance(input_cols, dict):
            col_map = input_cols
        else:
            col_map = {col: col for col in input_cols}

        for df in self.df_group:
            # param name: actual column name
            inputs = {
                param_name: df[col_name] for param_name, col_name in col_map.items()
            }
            result.append(df.with_columns(calculate(**inputs)))

        return pl.concat(result)
