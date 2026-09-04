from dataclasses import dataclass

import polars as pl
import talib

from stocksense.strategy.ta import BaseAccessor


@dataclass
class StatsAccessor(BaseAccessor):
    """Accessor for statistical technical indicators."""

    def beta(
        self, period: int = 5, high_col: str = "high", low_col: str = "low"
    ) -> pl.LazyFrame:
        """Beta."""

        def calculate(high, low):
            res = talib.BETA(high, low, timeperiod=period)
            return [pl.Series(f"BETA_{period}", res)]

        return self._apply_to_groups(
            {"high": high_col, "low": low_col}, calculate
        )

    def correl(
        self, period: int = 30, high_col: str = "high", low_col: str = "low"
    ) -> pl.LazyFrame:
        """Pearson's Correlation Coefficient (r)."""

        def calculate(high, low):
            res = talib.CORREL(high, low, timeperiod=period)
            return [pl.Series(f"CORREL_{period}", res)]

        return self._apply_to_groups(
            {"high": high_col, "low": low_col}, calculate
        )

    def linearreg(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """Linear Regression."""

        def calculate(real):
            res = talib.LINEARREG(real, timeperiod=period)
            return [pl.Series(f"LINEARREG_{period}", res)]

        return self._apply_to_groups({"real": col}, calculate)

    def linearreg_angle(
        self, period: int = 14, col: str = "close"
    ) -> pl.LazyFrame:
        """Linear Regression Angle."""

        def calculate(real):
            res = talib.LINEARREG_ANGLE(real, timeperiod=period)
            return [pl.Series(f"LINEARREG_ANGLE_{period}", res)]

        return self._apply_to_groups({"real": col}, calculate)

    def linearreg_intercept(
        self, period: int = 14, col: str = "close"
    ) -> pl.LazyFrame:
        """Linear Regression Intercept."""

        def calculate(real):
            res = talib.LINEARREG_INTERCEPT(real, timeperiod=period)
            return [pl.Series(f"LINEARREG_INTERCEPT_{period}", res)]

        return self._apply_to_groups({"real": col}, calculate)

    def linearreg_slope(
        self, period: int = 14, col: str = "close"
    ) -> pl.LazyFrame:
        """Linear Regression Slope."""

        def calculate(real):
            res = talib.LINEARREG_SLOPE(real, timeperiod=period)
            return [pl.Series(f"LINEARREG_SLOPE_{period}", res)]

        return self._apply_to_groups({"real": col}, calculate)

    def stddev(
        self, period: int = 5, nbdev: float = 1.0, col: str = "close"
    ) -> pl.LazyFrame:
        """Standard Deviation."""

        def calculate(real):
            res = talib.STDDEV(real, timeperiod=period, nbdev=nbdev)
            return [pl.Series(f"STDDEV_{period}", res)]

        return self._apply_to_groups({"real": col}, calculate)

    def tsf(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """Time Series Forecast."""

        def calculate(real):
            res = talib.TSF(real, timeperiod=period)
            return [pl.Series(f"TSF_{period}", res)]

        return self._apply_to_groups({"real": col}, calculate)

    def var(
        self, period: int = 5, nbdev: float = 1.0, col: str = "close"
    ) -> pl.LazyFrame:
        """Variance."""

        def calculate(real):
            res = talib.VAR(real, timeperiod=period, nbdev=nbdev)
            return [pl.Series(f"VAR_{period}", res)]

        return self._apply_to_groups({"real": col}, calculate)

