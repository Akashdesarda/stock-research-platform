from dataclasses import dataclass

import polars as pl
import talib


@dataclass
class VolumeAccessor:
    df: pl.LazyFrame

    def ad(self) -> pl.LazyFrame:
        """Chaikin A/D Line."""

        highs, lows, closes, volumes = (
            self.df.select(["high", "low", "close", "volume"]).collect().get_columns()
        )
        ad = talib.AD(
            highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), volumes.to_numpy()
        )
        return self.df.with_columns(pl.Series("AD", ad))

    def adosc(self, fastperiod: int = 3, slowperiod: int = 10) -> pl.LazyFrame:
        """Chaikin A/D Oscillator."""

        highs, lows, closes, volumes = (
            self.df.select(["high", "low", "close", "volume"]).collect().get_columns()
        )
        adosc = talib.ADOSC(
            highs.to_numpy(),
            lows.to_numpy(),
            closes.to_numpy(),
            volumes.to_numpy(),
            fastperiod=fastperiod,
            slowperiod=slowperiod,
        )
        return self.df.with_columns(
            pl.Series(f"ADOSC_{fastperiod}_{slowperiod}", adosc)
        )

    def obv(self, col: str = "close") -> pl.LazyFrame:
        """On Balance Volume."""
        close, volume = self.df.select([col, "volume"]).collect().get_columns()
        obv = talib.OBV(close.to_numpy(), volume.to_numpy())
        return self.df.with_columns(pl.Series("OBV", obv))
