from dataclasses import dataclass

import polars as pl
import talib


@dataclass
class OverlapStudyAccessor:
    df: pl.LazyFrame

    def bbands(
        self,
        period: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0,
        matype: int = 0,
        col: str = "close",
    ) -> pl.LazyFrame:
        """Bollinger Bands upper/middle/lower."""

        close = self.df.select(col).collect().to_series().to_numpy()
        upper, middle, lower = talib.BBANDS(
            close,
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=matype,
        )
        return self.df.with_columns([
            pl.Series(f"BBANDS_upper_{period}", upper),
            pl.Series(f"BBANDS_middle_{period}", middle),
            pl.Series(f"BBANDS_lower_{period}", lower),
        ])

    def dema(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Double Exponential Moving Average."""

        close = self.df.select(col).collect().to_series().to_numpy()
        dema = talib.DEMA(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"DEMA_{period}", dema))

    def ema(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Exponential Moving Average."""

        close = self.df.select(col).collect().to_series().to_numpy()
        ema = talib.EMA(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"EMA_{period}", ema))

    def ht_trendline(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Instantaneous Trendline."""

        close = self.df.select(col).collect().to_series().to_numpy()
        trendline = talib.HT_TRENDLINE(close)
        return self.df.with_columns(pl.Series("HT_TRENDLINE", trendline))

    def kama(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Kaufman Adaptive Moving Average."""

        close = self.df.select(col).collect().to_series().to_numpy()
        kama = talib.KAMA(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"KAMA_{period}", kama))

    def ma(self, period: int = 30, matype: int = 0, col: str = "close") -> pl.LazyFrame:
        """Generic Moving Average with type."""

        close = self.df.select(col).collect().to_series().to_numpy()
        ma = talib.MA(close, timeperiod=period, matype=matype)
        return self.df.with_columns(pl.Series(f"MA_{period}_{matype}", ma))

    def mama(
        self,
        fastlimit: float = 0.5,
        slowlimit: float = 0.05,
        col: str = "close",
    ) -> pl.LazyFrame:
        """MESA Adaptive Moving Average."""

        close = self.df.select(col).collect().to_series().to_numpy()
        mama, fama = talib.MAMA(close, fastlimit=fastlimit, slowlimit=slowlimit)
        return self.df.with_columns([
            pl.Series("MAMA", mama),
            pl.Series("FAMA", fama),
        ])

    def mavp(
        self,
        period_col: str,
        minperiod: int = 2,
        maxperiod: int = 30,
        matype: int = 0,
        col: str = "close",
    ) -> pl.LazyFrame:
        """Moving average with variable periods (expects period_col present)."""

        if period_col not in self.df.collect_schema().names():
            raise ValueError(f"period_col '{period_col}' not found in frame")

        close, periods = self.df.select([col, period_col]).collect().get_columns()
        mavp = talib.MAVP(
            close.to_numpy(),
            periods.to_numpy(),
            minperiod=minperiod,
            maxperiod=maxperiod,
            matype=matype,
        )
        return self.df.with_columns(pl.Series(f"MAVP_{minperiod}_{maxperiod}", mavp))

    def midpoint(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """MidPoint over period."""

        close = self.df.select(col).collect().to_series().to_numpy()
        midpoint = talib.MIDPOINT(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"MIDPOINT_{period}", midpoint))

    def midprice(self, period: int = 14) -> pl.LazyFrame:
        """Midpoint Price over period."""

        highs, lows = self.df.select(["high", "low"]).collect().get_columns()
        midprice = talib.MIDPRICE(highs.to_numpy(), lows.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"MIDPRICE_{period}", midprice))

    def sar(self, acceleration: float = 0.02, maximum: float = 0.2) -> pl.LazyFrame:
        """Parabolic SAR."""

        highs, lows = self.df.select(["high", "low"]).collect().get_columns()
        sar = talib.SAR(
            highs.to_numpy(),
            lows.to_numpy(),
            acceleration=acceleration,
            maximum=maximum,
        )
        return self.df.with_columns(pl.Series("SAR", sar))

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

        highs, lows = self.df.select(["high", "low"]).collect().get_columns()
        sarext = talib.SAREXT(
            highs.to_numpy(),
            lows.to_numpy(),
            startvalue=startvalue,
            offsetonreverse=offsetonreverse,
            accelerationinitlong=accelerationinitlong,
            accelerationlong=accelerationlong,
            accelerationmaxlong=accelerationmaxlong,
            accelerationinitshort=accelerationinitshort,
            accelerationshort=accelerationshort,
            accelerationmaxshort=accelerationmaxshort,
        )
        return self.df.with_columns(pl.Series("SAREXT", sarext))

    def sma(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Simple Moving Average."""

        close = self.df.select(col).collect().to_series().to_numpy()
        sma = talib.SMA(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"SMA_{period}", sma))

    def t3(
        self, period: int = 5, vfactor: float = 0.7, col: str = "close"
    ) -> pl.LazyFrame:
        """Triple Exponential Moving Average (T3)."""

        close = self.df.select(col).collect().to_series().to_numpy()
        t3 = talib.T3(close, timeperiod=period, vfactor=vfactor)
        suffix = f"{vfactor}".replace(".", "_")
        return self.df.with_columns(pl.Series(f"T3_{period}_{suffix}", t3))

    def tema(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Triple Exponential Moving Average."""

        close = self.df.select(col).collect().to_series().to_numpy()
        tema = talib.TEMA(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"TEMA_{period}", tema))

    def trima(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Triangular Moving Average."""

        close = self.df.select(col).collect().to_series().to_numpy()
        trima = talib.TRIMA(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"TRIMA_{period}", trima))

    def wma(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Weighted Moving Average."""

        close = self.df.select(col).collect().to_series().to_numpy()
        wma = talib.WMA(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"WMA_{period}", wma))
