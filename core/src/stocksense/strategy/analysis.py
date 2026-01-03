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

    def __post_init__(self):
        self._df = self.df.lazy() if isinstance(self.df, pl.DataFrame) else self.df
        # NOTE - cast to Float64 since TA-Lib expects float inputs
        self._df = self._df.cast({cs.numeric(): pl.Float64})

        # Basic validation - can be relaxed if needed
        required = {"open", "high", "low", "close", "volume"}
        if any(col not in self._df.collect_schema().names() for col in required):
            # Only warn or check subset to allow flexible usage
            pass

    @property
    def trend(self) -> TrendAccessor:

        return TrendAccessor(self._df)

    @property
    def momentum(self) -> MomentumAccessor:

        return MomentumAccessor(self._df)

    @property
    def volatility(self) -> VolatilityAccessor:

        return VolatilityAccessor(self._df)

    @property
    def volume(self) -> VolumeAccessor:

        return VolumeAccessor(self._df)

    @property
    def cycle(self) -> CycleAccessor:

        return CycleAccessor(self._df)

    @property
    def pattern(self) -> PatternRecognitionAccessor:

        return PatternRecognitionAccessor(self._df)

    @property
    def stats(self) -> StatsAccessor:

        return StatsAccessor(self._df)

    @property
    def overlap(self) -> OverlapStudyAccessor:

        return OverlapStudyAccessor(self._df)
