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
        # NOTE - cast to Float64 since TA-Lib expects float inputs
        self._df = self._df.cast({cs.numeric(): pl.Float64})

        schema_names = self._df.collect_schema().names()
        # Basic validation - can be relaxed if needed
        required = {"open", "high", "low", "close", "volume"}
        if any(col not in schema_names for col in required):
            # Only warn or check subset to allow flexible usage
            pass
        # validation for group by
        if self.group_by and self.group_by not in schema_names:
            raise ValueError(
                f"Group by column '{self.group_by}' not found in dataframe"
            )
        # validation for sort by
        if self.sort_by and self.sort_by not in schema_names:
            raise ValueError(f"Sort by column '{self.sort_by}' not found in dataframe")

    @property
    def trend(self) -> TrendAccessor:

        return TrendAccessor(self._df, self.group_by, self.sort_by, self.sort_desc)

    @property
    def momentum(self) -> MomentumAccessor:

        return MomentumAccessor(self._df, self.group_by, self.sort_by, self.sort_desc)

    @property
    def volatility(self) -> VolatilityAccessor:

        return VolatilityAccessor(self._df, self.group_by, self.sort_by, self.sort_desc)

    @property
    def volume(self) -> VolumeAccessor:

        return VolumeAccessor(self._df, self.group_by, self.sort_by, self.sort_desc)

    @property
    def cycle(self) -> CycleAccessor:

        return CycleAccessor(self._df, self.group_by, self.sort_by, self.sort_desc)

    @property
    def pattern(self) -> PatternRecognitionAccessor:

        return PatternRecognitionAccessor(
            self._df, self.group_by, self.sort_by, self.sort_desc
        )

    @property
    def stats(self) -> StatsAccessor:

        return StatsAccessor(self._df, self.group_by, self.sort_by, self.sort_desc)

    @property
    def overlap(self) -> OverlapStudyAccessor:

        return OverlapStudyAccessor(
            self._df, self.group_by, self.sort_by, self.sort_desc
        )
