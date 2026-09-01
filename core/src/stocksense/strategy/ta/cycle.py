from dataclasses import dataclass

import polars as pl
import talib

from stocksense.strategy.ta import BaseAccessor


@dataclass
class CycleAccessor(BaseAccessor):
    """Accessor for cycle-based technical indicators."""

    def ht_dcperiod(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Dominant Cycle Period."""

        def calculate(real):
            dcperiod = talib.HT_DCPERIOD(real)
            return [pl.Series("HT_DCPERIOD", dcperiod)]

        return self._apply_to_groups({"real": col}, calculate)

    def ht_dcphase(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Dominant Cycle Phase."""

        def calculate(real):
            dcphase = talib.HT_DCPHASE(real)
            return [pl.Series("HT_DCPHASE", dcphase)]

        return self._apply_to_groups({"real": col}, calculate)

    def ht_phasor(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Phasor Components (inphase, quadrature)."""

        def calculate(real):
            inphase, quadrature = talib.HT_PHASOR(real)
            return [
                pl.Series("HT_PHASOR_inphase", inphase),
                pl.Series("HT_PHASOR_quadrature", quadrature),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def ht_sine(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Sine and Lead Sine."""

        def calculate(real):
            sine, leadsine = talib.HT_SINE(real)
            return [
                pl.Series("HT_SINE", sine),
                pl.Series("HT_LEADSINE", leadsine),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def ht_trendmode(self, col: str = "close") -> pl.LazyFrame:
        """Hilbert Transform - Trend vs Cycle Mode."""

        def calculate(real):
            trendmode = talib.HT_TRENDMODE(real)
            return [pl.Series("HT_TRENDMODE", trendmode)]

        return self._apply_to_groups({"real": col}, calculate)
