from dataclasses import dataclass

import polars as pl
import talib

from stocksense.strategy.ta import BaseAccessor


@dataclass
class TrendAccessor(BaseAccessor):
    """Accessor for trend-based technical indicators."""

    def sma(self, period: int = 14, col: str = "close") -> pl.DataFrame:
        """Simple Moving Average."""
        expr = pl.col(col).rolling_mean(window_size=period)

        if self.group_by:
            expr = expr.over(self.group_by)

        return self.df.with_columns(expr.alias(f"SMA_{period}"))

    def sma_crossover(
        self, fast: int = 10, slow: int = 20, col: str = "close"
    ) -> pl.DataFrame:
        """Compute SMA fast/slow and crossover signal."""
        result = []
        for df in self.df_group:
            close = df[col].to_numpy()
            fast_sma = talib.SMA(close, timeperiod=fast)
            slow_sma = talib.SMA(close, timeperiod=slow)

            result.append(
                df.with_columns([
                    pl.Series(f"SMA_{fast}", fast_sma),
                    pl.Series(f"SMA_{slow}", slow_sma),
                ]).with_columns(
                    # computing new column based runtime columns needs `with_columns` again
                    (pl.col(f"SMA_{fast}") > pl.col(f"SMA_{slow}")).alias(
                        f"SMA_crossover_{fast}_{slow}"
                    )
                )
            )
        return pl.concat(result)

    def ema_crossover(
        self, fast: int = 12, slow: int = 26, col: str = "close"
    ) -> pl.DataFrame:
        """Compute EMA fast/slow and crossover signal."""
        result = []
        for df in self.df_group:
            close = df[col].to_numpy()
            fast_ema = talib.EMA(close, timeperiod=fast)
            slow_ema = talib.EMA(close, timeperiod=slow)

            result.append(
                df.with_columns([
                    pl.Series(f"EMA_{fast}", fast_ema),
                    pl.Series(f"EMA_{slow}", slow_ema),
                ]).with_columns(
                    # computing new column based runtime columns needs `with_columns` again
                    (pl.col(f"EMA_{fast}") > pl.col(f"EMA_{slow}")).alias(
                        f"EMA_crossover_{fast}_{slow}"
                    )
                )
            )
        return pl.concat(result)

    def macd(
        self,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
        col: str = "close",
    ) -> pl.DataFrame:
        """MACD line, signal, and histogram."""

        def calculate(real):
            macd, macdsignal, macdhist = talib.MACD(
                real,
                fastperiod=fastperiod,
                slowperiod=slowperiod,
                signalperiod=signalperiod,
            )
            return [
                pl.Series("MACD", macd),
                pl.Series("MACD_signal", macdsignal),
                pl.Series("MACD_hist", macdhist),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def adx_dmi(self, period: int = 14) -> pl.DataFrame:
        """Average Directional Index with +DI and -DI."""

        def calculate(high, low, close):
            adx = talib.ADX(high, low, close, timeperiod=period)
            plus_di = talib.PLUS_DI(high, low, close, timeperiod=period)
            minus_di = talib.MINUS_DI(high, low, close, timeperiod=period)
            return [
                pl.Series(f"ADX_{period}", adx),
                pl.Series(f"DI_plus_{period}", plus_di),
                pl.Series(f"DI_minus_{period}", minus_di),
            ]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def parabolic_sar(
        self, acceleration: float = 0.02, maximum: float = 0.2
    ) -> pl.DataFrame:
        """Parabolic SAR."""

        def calculate(high, low):
            sar = talib.SAR(
                high,
                low,
                acceleration=acceleration,
                maximum=maximum,
            )
            return [pl.Series("SAR", sar)]

        return self._apply_to_groups(["high", "low"], calculate)

    def kama(self, period: int = 30, col: str = "close") -> pl.DataFrame:
        """Kaufman Adaptive Moving Average."""

        def calculate(real):
            kama = talib.KAMA(real, timeperiod=period)
            return [pl.Series(f"KAMA_{period}", kama)]

        return self._apply_to_groups({"real": col}, calculate)

    def t3(
        self, period: int = 5, vfactor: float = 0.7, col: str = "close"
    ) -> pl.DataFrame:
        """T3 moving average variant."""

        def calculate(real):
            t3 = talib.T3(real, timeperiod=period, vfactor=vfactor)
            suffix = f"{vfactor}".replace(".", "_")
            return [pl.Series(f"T3_{period}_{suffix}", t3)]

        return self._apply_to_groups({"real": col}, calculate)
