from dataclasses import dataclass

import polars as pl
import talib

from stocksense.strategy.ta import BaseAccessor


@dataclass
class OverlapStudyAccessor(BaseAccessor):
    """Accessor for overlap study technical indicators."""

    def bbands(
        self,
        period: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0,
        col: str = "close",
    ) -> pl.LazyFrame:
        """Bollinger Bands upper/middle/lower."""

        def calculate(real):
            upper, middle, lower = talib.BBANDS(
                real, timeperiod=period, nbdevup=nbdevup, nbdevdn=nbdevdn
            )
            return [
                pl.Series(f"BBANDS_upper_{period}", upper),
                pl.Series(f"BBANDS_middle_{period}", middle),
                pl.Series(f"BBANDS_lower_{period}", lower),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def dema(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Double Exponential Moving Average."""

        def calculate(real):
            dema = talib.DEMA(real, timeperiod=period)
            return [pl.Series(f"DEMA_{period}", dema)]

        return self._apply_to_groups({"real": col}, calculate)

    def ema(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Exponential Moving Average."""

        def calculate(real):
            ema = talib.EMA(real, timeperiod=period)
            return [pl.Series(f"EMA_{period}", ema)]

        return self._apply_to_groups({"real": col}, calculate)

    def ht_trendline(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Instantaneous Trendline."""

        def calculate(real):
            trendline = talib.HT_TRENDLINE(real)
            return [pl.Series("HT_TRENDLINE", trendline)]

        return self._apply_to_groups({"real": col}, calculate)

    def kama(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Kaufman Adaptive Moving Average."""

        def calculate(real):
            kama = talib.KAMA(real, timeperiod=period)
            return [pl.Series(f"KAMA_{period}", kama)]

        return self._apply_to_groups({"real": col}, calculate)

    def ma(
        self, period: int = 30, matype: int = 0, col: str = "close"
    ) -> pl.LazyFrame:
        """Generic Moving Average with type."""

        def calculate(real):
            ma = talib.MA(real, timeperiod=period, matype=matype)
            return [pl.Series(f"MA_{period}_{matype}", ma)]

        return self._apply_to_groups({"real": col}, calculate)

    def mama(
        self,
        fastlimit: float = 0.5,
        slowlimit: float = 0.05,
        col: str = "close",
    ) -> pl.LazyFrame:
        """MESA Adaptive Moving Average."""

        def calculate(real):
            mama, fama = talib.MAMA(
                real, fastlimit=fastlimit, slowlimit=slowlimit
            )
            return [
                pl.Series("MAMA", mama),
                pl.Series("FAMA", fama),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def mavp(
        self,
        period_col: str,
        minperiod: int = 2,
        maxperiod: int = 30,
        col: str = "close",
    ) -> pl.LazyFrame:
        """Moving average with variable periods (expects period_col present)."""

        if period_col not in self.df.collect_schema().names():
            raise ValueError(f"period_col '{period_col}' not found in frame")

        def calculate(real, periods):
            mavp = talib.MAVP(
                real,
                periods,
                minperiod=minperiod,
                maxperiod=maxperiod,
            )
            return [pl.Series(f"MAVP_{minperiod}_{maxperiod}", mavp)]

        return self._apply_to_groups(
            {"real": col, "periods": period_col}, calculate
        )

    def midpoint(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """MidPoint over period."""

        def calculate(real):
            midpoint = talib.MIDPOINT(real, timeperiod=period)
            return [pl.Series(f"MIDPOINT_{period}", midpoint)]

        return self._apply_to_groups({"real": col}, calculate)

    def midprice(self, period: int = 14) -> pl.LazyFrame:
        """Midpoint Price over period."""

        def calculate(high, low):
            midprice = talib.MIDPRICE(high, low, timeperiod=period)
            return [pl.Series(f"MIDPRICE_{period}", midprice)]

        return self._apply_to_groups(["high", "low"], calculate)

    def sar(
        self, acceleration: float = 0.02, maximum: float = 0.2
    ) -> pl.LazyFrame:
        """Parabolic SAR."""

        def calculate(high, low):
            sar = talib.SAR(
                high, low, acceleration=acceleration, maximum=maximum
            )
            return [pl.Series("SAR", sar)]

        return self._apply_to_groups(["high", "low"], calculate)

    def sarext(
        self,
        startvalue: float = 0.0,
        offsetonreverse: float = 0.0,
        accelerationinitlong: float = 0.02,
        accelerationlong: float = 0.02,
        accelerationmaxlong: float = 0.2,
        accelerationinitshort: float = 0.02,
        accelerationshort: float = 0.02,
        accelerationmaxshort: float = 0.2,
    ) -> pl.LazyFrame:
        """Extended Parabolic SAR."""

        def calculate(high, low):
            sarext = talib.SAREXT(
                high,
                low,
                startvalue=startvalue,
                offsetonreverse=offsetonreverse,
                accelerationinitlong=accelerationinitlong,
                accelerationlong=accelerationlong,
                accelerationmaxlong=accelerationmaxlong,
                accelerationinitshort=accelerationinitshort,
                accelerationshort=accelerationshort,
                accelerationmaxshort=accelerationmaxshort,
            )
            return [pl.Series("SAREXT", sarext)]

        return self._apply_to_groups(["high", "low"], calculate)

    def sma(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Simple Moving Average."""

        def calculate(real):
            sma = talib.SMA(real, timeperiod=period)
            return [pl.Series(f"SMA_{period}", sma)]

        return self._apply_to_groups({"real": col}, calculate)

    def t3(
        self, period: int = 5, vfactor: float = 0.7, col: str = "close"
    ) -> pl.LazyFrame:
        """Triple Exponential Moving Average (T3)."""

        def calculate(real):
            t3 = talib.T3(real, timeperiod=period, vfactor=vfactor)
            suffix = f"{vfactor}".replace(".", "_")
            return [pl.Series(f"T3_{period}_{suffix}", t3)]

        return self._apply_to_groups({"real": col}, calculate)

    def tema(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Triple Exponential Moving Average."""

        def calculate(real):
            tema = talib.TEMA(real, timeperiod=period)
            return [pl.Series(f"TEMA_{period}", tema)]

        return self._apply_to_groups({"real": col}, calculate)

    def trima(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Triangular Moving Average."""

        def calculate(real):
            trima = talib.TRIMA(real, timeperiod=period)
            return [pl.Series(f"TRIMA_{period}", trima)]

        return self._apply_to_groups({"real": col}, calculate)

    def wma(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Weighted Moving Average."""

        def calculate(real):
            wma = talib.WMA(real, timeperiod=period)
            return [pl.Series(f"WMA_{period}", wma)]

        return self._apply_to_groups({"real": col}, calculate)
