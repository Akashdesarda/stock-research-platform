import polars as pl


class StatsAccessor:
    def __init__(self, df: pl.DataFrame | pl.LazyFrame):
        self._df = df
