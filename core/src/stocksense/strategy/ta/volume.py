from dataclasses import dataclass

import polars as pl
import talib

from stocksense.strategy.ta import BaseAccessor


@dataclass
class VolumeAccessor(BaseAccessor):
    """Accessor for volume-based technical indicators."""

    def ad(self) -> pl.DataFrame:
        """Chaikin A/D Line."""

        def calculate(high, low, close, volume):
            ad = talib.AD(high, low, close, volume)
            return [pl.Series("AD", ad)]

        return self._apply_to_groups(["high", "low", "close", "volume"], calculate)

    def adosc(self, fastperiod: int = 3, slowperiod: int = 10) -> pl.DataFrame:
        """Chaikin A/D Oscillator."""

        def calculate(high, low, close, volume):
            adosc = talib.ADOSC(high, low, close, volume, fastperiod, slowperiod)
            return [pl.Series(f"ADOSC_{fastperiod}_{slowperiod}", adosc)]

        return self._apply_to_groups(["high", "low", "close", "volume"], calculate)

    def obv(self, col: str = "close") -> pl.DataFrame:
        """On Balance Volume."""

        def calculate(real, volume):
            obv = talib.OBV(real, volume)
            return [pl.Series("OBV", obv)]

        return self._apply_to_groups({"real": col, "volume": "volume"}, calculate)
