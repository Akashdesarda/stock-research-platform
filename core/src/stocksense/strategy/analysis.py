from dataclasses import dataclass

import polars as pl
import polars.selectors as cs

from .ta.cycle import CycleAccessor
from .ta.momentum import MomentumAccessor
from .ta.overlap_study import OverlapStudyAccessor
from .ta.pattern_recognition import PatternRecognitionAccessor
from .ta.stats import StatsAccessor
from .ta.trend import TrendAccessor
from .ta.volatility import VolatilityAccessor
from .ta.volume import VolumeAccessor


@pl.api.register_dataframe_namespace("ta")
@pl.api.register_lazyframe_namespace("ta")
@dataclass
class TechnicalAnalysis:
    """
    Polars Namespace for Technical Analysis.
    Usage: df.ta.trend.sma(...)
    """

    df: pl.DataFrame | pl.LazyFrame
    group_by: str | None = None
    sort_by: str | None = None
    sort_desc: bool = False

    def __post_init__(self):
        self._df = self.df.collect() if isinstance(self.df, pl.LazyFrame) else self.df

        self._df = self._df.cast({cs.numeric(): pl.Float32})

        schema_names = self._df.columns

        required = {"open", "high", "low", "close", "volume"}
        if any(col not in schema_names for col in required):
            pass

        if self.group_by and self.group_by not in schema_names:
            raise ValueError(
                f"Group by column '{self.group_by}' not found in dataframe"
            )

        if self.sort_by and self.sort_by not in schema_names:
            raise ValueError(f"Sort by column '{self.sort_by}' not found in dataframe")

        if self.group_by and self.sort_by:
            self._df = self._df.sort(
                [self.group_by, self.sort_by], descending=self.sort_desc
            )
        elif self.sort_by:
            self._df = self._df.sort(self.sort_by, descending=self.sort_desc)

    def apply(self, accessor: str, method: str, **parameters) -> pl.DataFrame:
        """Apply a technical analysis method to the dataframe"""
        # get the accessor and method E.G. ta.trend.sma(period=10)
        strategy_method = getattr(getattr(self, accessor), method)
        self._df = strategy_method(**parameters)
        return self._df

    @property
    def trend(self) -> TrendAccessor:

        return TrendAccessor(self._df, self.group_by)

    @property
    def momentum(self) -> MomentumAccessor:

        return MomentumAccessor(self._df, self.group_by)

    @property
    def volatility(self) -> VolatilityAccessor:

        return VolatilityAccessor(self._df, self.group_by)

    @property
    def volume(self) -> VolumeAccessor:

        return VolumeAccessor(self._df, self.group_by)

    @property
    def cycle(self) -> CycleAccessor:

        return CycleAccessor(self._df, self.group_by)

    @property
    def pattern(self) -> PatternRecognitionAccessor:

        return PatternRecognitionAccessor(self._df, self.group_by)

    @property
    def stats(self) -> StatsAccessor:

        return StatsAccessor(self._df, self.group_by)

    @property
    def overlap(self) -> OverlapStudyAccessor:

        return OverlapStudyAccessor(self._df, self.group_by)
