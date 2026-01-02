from dataclasses import dataclass

import polars as pl
import talib


@dataclass
class VolatilityAccessor:
    df: pl.LazyFrame

    def atr(self, period: int = 14) -> pl.LazyFrame:
        """Average True Range."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        atr = talib.ATR(
            highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period
        )
        return self.df.with_columns(pl.Series(f"ATR_{period}", atr))

    def natr(self, period: int = 14) -> pl.LazyFrame:
        """Normalized Average True Range."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        natr = talib.NATR(
            highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period
        )
        return self.df.with_columns(pl.Series(f"NATR_{period}", natr))

    def trange(self) -> pl.LazyFrame:
        """True Range."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        tr = talib.TRANGE(highs.to_numpy(), lows.to_numpy(), closes.to_numpy())
        return self.df.with_columns(pl.Series("TRANGE", tr))
