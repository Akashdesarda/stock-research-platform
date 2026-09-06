from dataclasses import dataclass

import polars as pl
import talib

from stocksense.strategy.ta import BaseAccessor


@dataclass
class VolatilityAccessor(BaseAccessor):
    """Accessor for volatility-based technical indicators."""

    def atr(self, period: int = 14) -> pl.DataFrame:
        """Average True Range."""

        def calculate(high, low, close):
            atr = talib.ATR(high, low, close, timeperiod=period)
            return [pl.Series(f"ATR_{period}", atr)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def natr(self, period: int = 14) -> pl.DataFrame:
        """Normalized Average True Range."""

        def calculate(high, low, close):
            natr = talib.NATR(high, low, close, timeperiod=period)
            return [pl.Series(f"NATR_{period}", natr)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def trange(self) -> pl.DataFrame:
        """True Range."""

        def calculate(high, low, close):
            tr = talib.TRANGE(high, low, close)
            return [pl.Series("TRANGE", tr)]

        return self._apply_to_groups(["high", "low", "close"], calculate)
