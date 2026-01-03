from dataclasses import dataclass

import polars as pl
import talib


@dataclass
class CycleAccessor:
    df: pl.LazyFrame

    def ht_dcperiod(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Dominant Cycle Period."""

        close = self.df.select(col).collect().to_series().to_numpy()
        dcperiod = talib.HT_DCPERIOD(close)
        return self.df.with_columns(pl.Series("HT_DCPERIOD", dcperiod))

    def ht_dcphase(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Dominant Cycle Phase."""

        close = self.df.select(col).collect().to_series().to_numpy()
        dcphase = talib.HT_DCPHASE(close)
        return self.df.with_columns(pl.Series("HT_DCPHASE", dcphase))

    def ht_phasor(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Phasor Components (inphase, quadrature)."""

        close = self.df.select(col).collect().to_series().to_numpy()
        inphase, quadrature = talib.HT_PHASOR(close)
        return self.df.with_columns([
            pl.Series("HT_PHASOR_inphase", inphase),
            pl.Series("HT_PHASOR_quadrature", quadrature),
        ])

    def ht_sine(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Sine and Lead Sine."""

        close = self.df.select(col).collect().to_series().to_numpy()
        sine, leadsine = talib.HT_SINE(close)
        return self.df.with_columns([
            pl.Series("HT_SINE", sine),
            pl.Series("HT_LEADSINE", leadsine),
        ])

    def ht_trendmode(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Trend vs Cycle Mode."""

        close = self.df.select(col).collect().to_series().to_numpy()
        trendmode = talib.HT_TRENDMODE(close)
        return self.df.with_columns(pl.Series("HT_TRENDMODE", trendmode))
