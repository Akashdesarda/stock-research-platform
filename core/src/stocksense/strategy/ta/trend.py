from dataclasses import dataclass

import polars as pl
import talib


@dataclass
class TrendAccessor:
    df: pl.LazyFrame

    def sma(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """Simple Moving Average"""
        return self.df.with_columns(
            pl.col(col).rolling_mean(window_size=period).alias(f"SMA_{period}")
        )

    def sma_crossover(
        self, fast: int = 10, slow: int = 20, col: str = "close"
    ) -> pl.LazyFrame:
        """Compute SMA fast/slow and crossover signal."""

        close = self.df.select(col).collect().to_series().to_numpy()
        fast_sma = talib.SMA(close, timeperiod=fast)
        slow_sma = talib.SMA(close, timeperiod=slow)

        return self.df.with_columns([
            pl.Series(f"SMA_{fast}", fast_sma),
            pl.Series(f"SMA_{slow}", slow_sma),
        ]).with_columns(
            # computing new column based runtime columns needs `with_columns` again
            (pl.col(f"SMA_{fast}") > pl.col(f"SMA_{slow}")).alias(
                f"SMA_crossover_{fast}_{slow}"
            )
        )

    def ema_crossover(
        self, fast: int = 12, slow: int = 26, col: str = "close"
    ) -> pl.LazyFrame:
        """Compute EMA fast/slow and crossover signal."""

        close = self.df.select(col).collect().to_series().to_numpy()
        fast_ema = talib.EMA(close, timeperiod=fast)
        slow_ema = talib.EMA(close, timeperiod=slow)

        return self.df.with_columns([
            pl.Series(f"EMA_{fast}", fast_ema),
            pl.Series(f"EMA_{slow}", slow_ema),
        ]).with_columns(
            # computing new column based runtime columns needs `with_columns` again
            (pl.col(f"EMA_{fast}") > pl.col(f"EMA_{slow}")).alias(
                f"EMA_crossover_{fast}_{slow}"
            )
        )

    def macd(
        self,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
        col: str = "close",
    ) -> pl.LazyFrame:
        """MACD line, signal, and histogram."""

        close = self.df.select(col).collect().to_series().to_numpy()
        macd, macdsignal, macdhist = talib.MACD(
            close,
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod,
        )
        return self.df.with_columns([
            pl.Series("MACD", macd),
            pl.Series("MACD_signal", macdsignal),
            pl.Series("MACD_hist", macdhist),
        ])

    def adx_dmi(self, period: int = 14) -> pl.LazyFrame:
        """Average Directional Index with +DI and -DI."""

        high = self.df.select("high").collect().to_series().to_numpy()
        low = self.df.select("low").collect().to_series().to_numpy()
        close = self.df.select("close").collect().to_series().to_numpy()
        adx = talib.ADX(high, low, close, timeperiod=period)
        plus_di = talib.PLUS_DI(high, low, close, timeperiod=period)
        minus_di = talib.MINUS_DI(high, low, close, timeperiod=period)
        return self.df.with_columns([
            pl.Series(f"ADX_{period}", adx),
            pl.Series(f"DI_plus_{period}", plus_di),
            pl.Series(f"DI_minus_{period}", minus_di),
        ])

    def parabolic_sar(
        self, acceleration: float = 0.02, maximum: float = 0.2
    ) -> pl.LazyFrame:
        """Parabolic SAR."""

        sar = talib.SAR(
            self.df.select("high").collect().to_series().to_numpy(),
            self.df.select("low").collect().to_series().to_numpy(),
            acceleration=acceleration,
            maximum=maximum,
        )
        return self.df.with_columns(pl.Series("SAR", sar))

    def kama(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Kaufman Adaptive Moving Average."""

        kama = talib.KAMA(
            self.df.select(col).collect().to_series().to_numpy(), timeperiod=period
        )
        return self.df.with_columns(pl.Series(f"KAMA_{period}", kama))

    def t3(
        self, period: int = 5, vfactor: float = 0.7, col: str = "close"
    ) -> pl.LazyFrame:
        """T3 moving average variant."""

        t3 = talib.T3(
            self.df.select(col).collect().to_series().to_numpy(),
            timeperiod=period,
            vfactor=vfactor,
        )
        suffix = f"{vfactor}".replace(".", "_")
        return self.df.with_columns(pl.Series(f"T3_{period}_{suffix}", t3))
