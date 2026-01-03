from dataclasses import dataclass

import polars as pl
import talib


@dataclass
class MomentumAccessor:
    df: pl.LazyFrame

    def rsi(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """Relative Strength Index."""

        close = self.df.select(col).collect().to_series().to_numpy()
        rsi = talib.RSI(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"RSI_{period}", rsi))

    def stoch_rsi(
        self,
        timeperiod: int = 14,
        fastk_period: int = 5,
        fastd_period: int = 3,
        fastd_matype: int = 0,
        col: str = "close",
    ) -> pl.LazyFrame:
        """Stochastic RSI fast %K and %D."""

        close = self.df.select(col).collect().to_series().to_numpy()
        fastk, fastd = talib.STOCHRSI(
            close,
            timeperiod=timeperiod,
            fastk_period=fastk_period,
            fastd_period=fastd_period,
            fastd_matype=fastd_matype,
        )
        return self.df.with_columns([
            pl.Series(f"StochRSI_fastk_{timeperiod}", fastk),
            pl.Series(f"StochRSI_fastd_{timeperiod}", fastd),
        ])

    def stochastic(
        self,
        fastk_period: int = 5,
        slowk_period: int = 3,
        slowk_matype: int = 0,
        slowd_period: int = 3,
        slowd_matype: int = 0,
    ) -> pl.LazyFrame:
        """Stochastic Oscillator %K and %D."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        slowk, slowd = talib.STOCH(
            highs.to_numpy(),
            lows.to_numpy(),
            closes.to_numpy(),
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowk_matype=slowk_matype,
            slowd_period=slowd_period,
            slowd_matype=slowd_matype,
        )
        return self.df.with_columns([
            pl.Series("STOCH_slowk", slowk),
            pl.Series("STOCH_slowd", slowd),
        ])

    def cci(self, period: int = 14) -> pl.LazyFrame:
        """Commodity Channel Index."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        cci = talib.CCI(
            highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period
        )
        return self.df.with_columns(pl.Series(f"CCI_{period}", cci))

    def roc(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Rate of Change."""

        close = self.df.select(col).collect().to_series().to_numpy()
        roc = talib.ROC(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"ROC_{period}", roc))

    def momentum(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Momentum indicator (MOM)."""

        close = self.df.select(col).collect().to_series().to_numpy()
        mom = talib.MOM(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"MOM_{period}", mom))

    def williams_r(self, period: int = 14) -> pl.LazyFrame:
        """Williams %R."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        willr = talib.WILLR(
            highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period
        )
        return self.df.with_columns(pl.Series(f"WILLR_{period}", willr))

    def trix(self, period: int = 30, col: str = "close") -> pl.LazyFrame:
        """Triple Exponential Average (TRIX)."""

        close = self.df.select(col).collect().to_series().to_numpy()
        trix = talib.TRIX(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"TRIX_{period}", trix))

    def adx(self, period: int = 14) -> pl.LazyFrame:
        """Average Directional Movement Index."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        adx = talib.ADX(highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"ADX_{period}", adx))

    def adxr(self, period: int = 14) -> pl.LazyFrame:
        """Average Directional Movement Index Rating."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        adxr = talib.ADXR(highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"ADXR_{period}", adxr))

    def apo(self, fastperiod: int = 12, slowperiod: int = 26, matype: int = 0, col: str = "close") -> pl.LazyFrame:
        """Absolute Price Oscillator."""

        close = self.df.select(col).collect().to_series().to_numpy()
        apo = talib.APO(close, fastperiod=fastperiod, slowperiod=slowperiod, matype=matype)
        return self.df.with_columns(pl.Series(f"APO_{fastperiod}_{slowperiod}", apo))

    def aroon(self, period: int = 14) -> pl.LazyFrame:
        """Aroon up and down."""

        highs, lows = self.df.select(["high", "low"]).collect().get_columns()
        aroondown, aroonup = talib.AROON(highs.to_numpy(), lows.to_numpy(), timeperiod=period)
        return self.df.with_columns([
            pl.Series(f"AROON_down_{period}", aroondown),
            pl.Series(f"AROON_up_{period}", aroonup),
        ])

    def aroonosc(self, period: int = 14) -> pl.LazyFrame:
        """Aroon Oscillator."""

        highs, lows = self.df.select(["high", "low"]).collect().get_columns()
        osc = talib.AROONOSC(highs.to_numpy(), lows.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"AROONOSC_{period}", osc))

    def bop(self) -> pl.LazyFrame:
        """Balance of Power."""

        opens, highs, lows, closes = (
            self.df.select(["open", "high", "low", "close"]).collect().get_columns()
        )
        bop = talib.BOP(opens.to_numpy(), highs.to_numpy(), lows.to_numpy(), closes.to_numpy())
        return self.df.with_columns(pl.Series("BOP", bop))

    def cmo(self, period: int = 14, col: str = "close") -> pl.LazyFrame:
        """Chande Momentum Oscillator."""

        close = self.df.select(col).collect().to_series().to_numpy()
        cmo = talib.CMO(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"CMO_{period}", cmo))

    def dx(self, period: int = 14) -> pl.LazyFrame:
        """Directional Movement Index."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        dx = talib.DX(highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"DX_{period}", dx))

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

    def macdext(
        self,
        fastperiod: int = 12,
        fastmatype: int = 0,
        slowperiod: int = 26,
        slowmatype: int = 0,
        signalperiod: int = 9,
        signalmatype: int = 0,
        col: str = "close",
    ) -> pl.LazyFrame:
        """MACD with configurable MA types."""

        close = self.df.select(col).collect().to_series().to_numpy()
        macd, macdsignal, macdhist = talib.MACDEXT(
            close,
            fastperiod=fastperiod,
            fastmatype=fastmatype,
            slowperiod=slowperiod,
            slowmatype=slowmatype,
            signalperiod=signalperiod,
            signalmatype=signalmatype,
        )
        return self.df.with_columns([
            pl.Series("MACDEXT", macd),
            pl.Series("MACDEXT_signal", macdsignal),
            pl.Series("MACDEXT_hist", macdhist),
        ])

    def macdfix(self, signalperiod: int = 9, col: str = "close") -> pl.LazyFrame:
        """MACD Fix 12/26 with variable signal period."""

        close = self.df.select(col).collect().to_series().to_numpy()
        macd, macdsignal, macdhist = talib.MACDFIX(close, signalperiod=signalperiod)
        return self.df.with_columns([
            pl.Series("MACDFIX", macd),
            pl.Series("MACDFIX_signal", macdsignal),
            pl.Series("MACDFIX_hist", macdhist),
        ])

    def mfi(self, period: int = 14) -> pl.LazyFrame:
        """Money Flow Index."""

        highs, lows, closes, volumes = (
            self.df.select(["high", "low", "close", "volume"]).collect().get_columns()
        )
        mfi = talib.MFI(highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), volumes.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"MFI_{period}", mfi))

    def minus_di(self, period: int = 14) -> pl.LazyFrame:
        """Minus Directional Indicator."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        mdi = talib.MINUS_DI(highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"MINUS_DI_{period}", mdi))

    def minus_dm(self, period: int = 14) -> pl.LazyFrame:
        """Minus Directional Movement."""

        highs, lows = self.df.select(["high", "low"]).collect().get_columns()
        mdm = talib.MINUS_DM(highs.to_numpy(), lows.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"MINUS_DM_{period}", mdm))

    def plus_di(self, period: int = 14) -> pl.LazyFrame:
        """Plus Directional Indicator."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        pdi = talib.PLUS_DI(highs.to_numpy(), lows.to_numpy(), closes.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"PLUS_DI_{period}", pdi))

    def plus_dm(self, period: int = 14) -> pl.LazyFrame:
        """Plus Directional Movement."""

        highs, lows = self.df.select(["high", "low"]).collect().get_columns()
        pdm = talib.PLUS_DM(highs.to_numpy(), lows.to_numpy(), timeperiod=period)
        return self.df.with_columns(pl.Series(f"PLUS_DM_{period}", pdm))

    def ppo(self, fastperiod: int = 12, slowperiod: int = 26, matype: int = 0, col: str = "close") -> pl.LazyFrame:
        """Percentage Price Oscillator."""

        close = self.df.select(col).collect().to_series().to_numpy()
        ppo = talib.PPO(close, fastperiod=fastperiod, slowperiod=slowperiod, matype=matype)
        return self.df.with_columns(pl.Series(f"PPO_{fastperiod}_{slowperiod}", ppo))

    def rocp(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Rate of Change Percentage."""

        close = self.df.select(col).collect().to_series().to_numpy()
        rocp = talib.ROCP(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"ROCP_{period}", rocp))

    def rocr(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Rate of Change Ratio."""

        close = self.df.select(col).collect().to_series().to_numpy()
        rocr = talib.ROCR(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"ROCR_{period}", rocr))

    def rocr100(self, period: int = 10, col: str = "close") -> pl.LazyFrame:
        """Rate of Change Ratio scaled to 100."""

        close = self.df.select(col).collect().to_series().to_numpy()
        rocr100 = talib.ROCR100(close, timeperiod=period)
        return self.df.with_columns(pl.Series(f"ROCR100_{period}", rocr100))

    def stochf(
        self,
        fastk_period: int = 5,
        fastd_period: int = 3,
        fastd_matype: int = 0,
    ) -> pl.LazyFrame:
        """Stochastic Fast %K and %D."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        fastk, fastd = talib.STOCHF(
            highs.to_numpy(),
            lows.to_numpy(),
            closes.to_numpy(),
            fastk_period=fastk_period,
            fastd_period=fastd_period,
            fastd_matype=fastd_matype,
        )
        return self.df.with_columns([
            pl.Series("STOCHF_fastk", fastk),
            pl.Series("STOCHF_fastd", fastd),
        ])

    def ultosc(
        self,
        timeperiod1: int = 7,
        timeperiod2: int = 14,
        timeperiod3: int = 28,
    ) -> pl.LazyFrame:
        """Ultimate Oscillator."""

        highs, lows, closes = (
            self.df.select(["high", "low", "close"]).collect().get_columns()
        )
        ult = talib.ULTOSC(
            highs.to_numpy(),
            lows.to_numpy(),
            closes.to_numpy(),
            timeperiod1=timeperiod1,
            timeperiod2=timeperiod2,
            timeperiod3=timeperiod3,
        )
        return self.df.with_columns(pl.Series("ULTOSC", ult))
