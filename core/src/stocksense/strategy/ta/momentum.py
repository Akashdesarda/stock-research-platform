from dataclasses import dataclass

import polars as pl
import talib

from stocksense.strategy.ta import BaseAccessor


@dataclass
class MomentumAccessor(BaseAccessor):
    """Accessor for momentum-based technical indicators."""

    def rsi(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """Relative Strength Index."""

        def calculate(real):
            rsi = talib.RSI(real, timeperiod=period)
            return [pl.Series(f"RSI_{period}", rsi)]

        return self._apply_to_groups({"real": col}, calculate)

    def stoch_rsi(
        self,
        timeperiod: int = 14,
        fastk_period: int = 5,
        fastd_period: int = 3,
        col: str = "close",
    ) -> pl.LazyFrame:
        """Stochastic RSI fast %K and %D."""

        def calculate(real):
            fastk, fastd = talib.STOCHRSI(
                real, timeperiod, fastk_period, fastd_period
            )
            return [
                pl.Series(f"StochRSI_fastk_{timeperiod}", fastk),
                pl.Series(f"StochRSI_fastd_{timeperiod}", fastd),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def stochastic(
        self,
        fastk_period: int = 5,
        slowk_period: int = 3,
        slowd_period: int = 3,
    ) -> pl.LazyFrame:
        """Stochastic Oscillator %K and %D."""

        def calculate(high, low, close):
            slowk, slowd = talib.STOCH(
                high,
                low,
                close,
                fastk_period=fastk_period,
                slowk_period=slowk_period,
                slowd_period=slowd_period,
            )
            return [
                pl.Series("STOCH_slowk", slowk),
                pl.Series("STOCH_slowd", slowd),
            ]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def cci(self, period: int = 14) -> pl.LazyFrame:
        """Commodity Channel Index."""

        def calculate(high, low, close):
            cci = talib.CCI(high, low, close, timeperiod=period)
            return [pl.Series(f"CCI_{period}", cci)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def roc(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Rate of Change."""

        def calculate(real):
            roc = talib.ROC(real, timeperiod=period)
            return [pl.Series(f"ROC_{period}", roc)]

        return self._apply_to_groups({"real": col}, calculate)

    def momentum(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Momentum indicator (MOM)."""

        def calculate(real):
            mom = talib.MOM(real, timeperiod=period)
            return [pl.Series(f"MOM_{period}", mom)]

        return self._apply_to_groups({"real": col}, calculate)

    def williams_r(self, period: int = 14) -> pl.LazyFrame:
        """Williams %R."""

        def calculate(high, low, close):
            willr = talib.WILLR(high, low, close, timeperiod=period)
            return [pl.Series(f"WILLR_{period}", willr)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def trix(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Triple Exponential Average (TRIX)."""

        def calculate(real):
            trix = talib.TRIX(real, timeperiod=period)
            return [pl.Series(f"TRIX_{period}", trix)]

        return self._apply_to_groups({"real": col}, calculate)

    def adx(self, period: int = 14) -> pl.LazyFrame:
        """Average Directional Movement Index."""

        def calculate(high, low, close):
            adx = talib.ADX(high, low, close, timeperiod=period)
            return [pl.Series(f"ADX_{period}", adx)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def adxr(self, period: int = 14) -> pl.LazyFrame:
        """Average Directional Movement Index Rating."""

        def calculate(high, low, close):
            adxr = talib.ADXR(high, low, close, timeperiod=period)
            return [pl.Series(f"ADXR_{period}", adxr)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def apo(
        self, fastperiod: int = 12, slowperiod: int = 26, col: str = "close"
    ) -> pl.LazyFrame:
        """Absolute Price Oscillator."""

        def calculate(real):
            apo = talib.APO(real, fastperiod, slowperiod)
            return [pl.Series(f"APO_{fastperiod}_{slowperiod}", apo)]

        return self._apply_to_groups({"real": col}, calculate)

    def aroon(self, period: int = 14) -> pl.LazyFrame:
        """Aroon up and down."""

        def calculate(high, low):
            aroondown, aroonup = talib.AROON(high, low, timeperiod=period)
            return [
                pl.Series(f"AROON_down_{period}", aroondown),
                pl.Series(f"AROON_up_{period}", aroonup),
            ]

        return self._apply_to_groups(["high", "low"], calculate)

    def aroonosc(self, period: int = 14) -> pl.LazyFrame:
        """Aroon Oscillator."""

        def calculate(high, low):
            osc = talib.AROONOSC(high, low, timeperiod=period)
            return [pl.Series(f"AROONOSC_{period}", osc)]

        return self._apply_to_groups(["high", "low"], calculate)

    def bop(self) -> pl.LazyFrame:
        """Balance of Power."""

        def calculate(open, high, low, close):
            bop = talib.BOP(open, high, low, close)
            return [pl.Series("BOP", bop)]

        return self._apply_to_groups(
            ["open", "high", "low", "close"], calculate
        )

    def cmo(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """Chande Momentum Oscillator."""

        def calculate(real):
            cmo = talib.CMO(real, timeperiod=period)
            return [pl.Series(f"CMO_{period}", cmo)]

        return self._apply_to_groups({"real": col}, calculate)

    def dx(self, period: int = 14) -> pl.LazyFrame:
        """Directional Movement Index."""

        def calculate(high, low, close):
            dx = talib.DX(high, low, close, timeperiod=period)
            return [pl.Series(f"DX_{period}", dx)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def macd(
        self,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
        col: str = "close",
    ) -> pl.LazyFrame:
        """MACD line, signal, and histogram."""

        def calculate(real):
            macd, macdsignal, macdhist = talib.MACD(
                real, fastperiod, slowperiod, signalperiod
            )
            return [
                pl.Series("MACD", macd),
                pl.Series("MACD_signal", macdsignal),
                pl.Series("MACD_hist", macdhist),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def macdext(
        self,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
        col: str = "close",
    ) -> pl.LazyFrame:
        """MACD with configurable MA types."""

        def calculate(real):
            macd, macdsignal, macdhist = talib.MACDEXT(
                real,
                fastperiod=fastperiod,
                slowperiod=slowperiod,
                signalperiod=signalperiod,
            )
            return [
                pl.Series("MACDEXT", macd),
                pl.Series("MACDEXT_signal", macdsignal),
                pl.Series("MACDEXT_hist", macdhist),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def macdfix(
        self, signalperiod: int = 9, col: str = "close"
    ) -> pl.LazyFrame:
        """MACD Fix 12/26 with variable signal period."""

        def calculate(real):
            macd, macdsignal, macdhist = talib.MACDFIX(
                real, signalperiod=signalperiod
            )
            return [
                pl.Series("MACDFIX", macd),
                pl.Series("MACDFIX_signal", macdsignal),
                pl.Series("MACDFIX_hist", macdhist),
            ]

        return self._apply_to_groups({"real": col}, calculate)

    def mfi(self, period: int = 14) -> pl.LazyFrame:
        """Money Flow Index."""

        def calculate(high, low, close, volume):
            mfi = talib.MFI(high, low, close, volume, timeperiod=period)
            return [pl.Series(f"MFI_{period}", mfi)]

        return self._apply_to_groups(
            ["high", "low", "close", "volume"], calculate
        )

    def minus_di(self, period: int = 14) -> pl.LazyFrame:
        """Minus Directional Indicator."""

        def calculate(high, low, close):
            mdi = talib.MINUS_DI(high, low, close, timeperiod=period)
            return [pl.Series(f"MINUS_DI_{period}", mdi)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def minus_dm(self, period: int = 14) -> pl.LazyFrame:
        """Minus Directional Movement."""

        def calculate(high, low):
            mdm = talib.MINUS_DM(high, low, timeperiod=period)
            return [pl.Series(f"MINUS_DM_{period}", mdm)]

        return self._apply_to_groups(["high", "low"], calculate)

    def plus_di(self, period: int = 14) -> pl.LazyFrame:
        """Plus Directional Indicator."""

        def calculate(high, low, close):
            pdi = talib.PLUS_DI(high, low, close, timeperiod=period)
            return [pl.Series(f"PLUS_DI_{period}", pdi)]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def plus_dm(self, period: int = 14) -> pl.LazyFrame:
        """Plus Directional Movement."""

        def calculate(high, low):
            pdm = talib.PLUS_DM(high, low, timeperiod=period)
            return [pl.Series(f"PLUS_DM_{period}", pdm)]

        return self._apply_to_groups(["high", "low"], calculate)

    def ppo(
        self, fastperiod: int = 12, slowperiod: int = 26, col: str = "close"
    ) -> pl.LazyFrame:
        """Percentage Price Oscillator."""

        def calculate(real):
            ppo = talib.PPO(real, fastperiod, slowperiod)
            return [pl.Series(f"PPO_{fastperiod}_{slowperiod}", ppo)]

        return self._apply_to_groups({"real": col}, calculate)

    def rocp(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Rate of Change Percentage."""

        def calculate(real):
            rocp = talib.ROCP(real, timeperiod=period)
            return [pl.Series(f"ROCP_{period}", rocp)]

        return self._apply_to_groups({"real": col}, calculate)

    def rocr(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Rate of Change Ratio."""

        def calculate(real):
            rocr = talib.ROCR(real, timeperiod=period)
            return [pl.Series(f"ROCR_{period}", rocr)]

        return self._apply_to_groups({"real": col}, calculate)

    def rocr100(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Rate of Change Ratio scaled to 100."""

        def calculate(real):
            rocr100 = talib.ROCR100(real, timeperiod=period)
            return [pl.Series(f"ROCR100_{period}", rocr100)]

        return self._apply_to_groups({"real": col}, calculate)

    def stochf(
        self, fastk_period: int = 5, fastd_period: int = 3
    ) -> pl.LazyFrame:
        """Stochastic Fast %K and %D."""

        def calculate(high, low, close):
            fastk, fastd = talib.STOCHF(
                high, low, close, fastk_period, fastd_period
            )
            return [
                pl.Series("STOCHF_fastk", fastk),
                pl.Series("STOCHF_fastd", fastd),
            ]

        return self._apply_to_groups(["high", "low", "close"], calculate)

    def ultosc(
        self, timeperiod1: int = 7, timeperiod2: int = 14, timeperiod3: int = 28
    ) -> pl.LazyFrame:
        """Ultimate Oscillator."""

        def calculate(high, low, close):
            ult = talib.ULTOSC(
                high, low, close, timeperiod1, timeperiod2, timeperiod3
            )
            return [pl.Series("ULTOSC", ult)]

        return self._apply_to_groups(["high", "low", "close"], calculate)
