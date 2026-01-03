from dataclasses import dataclass

import polars as pl
import talib


@dataclass
class PatternRecognitionAccessor:
    df: pl.LazyFrame

    def _apply_pattern(self, func, name: str, **kwargs) -> pl.LazyFrame:
        opens, highs, lows, closes = (
            self.df.select(["open", "high", "low", "close"]).collect().get_columns()
        )
        values = func(
            opens.to_numpy(),
            highs.to_numpy(),
            lows.to_numpy(),
            closes.to_numpy(),
            **kwargs,
        )
        return self.df.with_columns(pl.Series(name, values))

    def cdl2crows(self) -> pl.LazyFrame:
        """Two Crows."""

        return self._apply_pattern(talib.CDL2CROWS, "CDL2CROWS")

    def cdl3blackcrows(self) -> pl.LazyFrame:
        """Three Black Crows."""

        return self._apply_pattern(talib.CDL3BLACKCROWS, "CDL3BLACKCROWS")

    def cdl3inside(self) -> pl.LazyFrame:
        """Three Inside Up/Down."""

        return self._apply_pattern(talib.CDL3INSIDE, "CDL3INSIDE")

    def cdl3linestrike(self) -> pl.LazyFrame:
        """Three-Line Strike."""

        return self._apply_pattern(talib.CDL3LINESTRIKE, "CDL3LINESTRIKE")

    def cdl3outside(self) -> pl.LazyFrame:
        """Three Outside Up/Down."""

        return self._apply_pattern(talib.CDL3OUTSIDE, "CDL3OUTSIDE")

    def cdl3starsinsouth(self) -> pl.LazyFrame:
        """Three Stars In The South."""

        return self._apply_pattern(talib.CDL3STARSINSOUTH, "CDL3STARSINSOUTH")

    def cdl3whitesoldiers(self) -> pl.LazyFrame:
        """Three Advancing White Soldiers."""

        return self._apply_pattern(talib.CDL3WHITESOLDIERS, "CDL3WHITESOLDIERS")

    def cdlabandonedbaby(self, penetration: float = 0.3) -> pl.LazyFrame:
        """Abandoned Baby."""

        return self._apply_pattern(
            talib.CDLABANDONEDBABY, "CDLABANDONEDBABY", penetration=penetration
        )

    def cdladvanceblock(self) -> pl.LazyFrame:
        """Advance Block."""

        return self._apply_pattern(talib.CDLADVANCEBLOCK, "CDLADVANCEBLOCK")

    def cdlbelthold(self) -> pl.LazyFrame:
        """Belt-hold."""

        return self._apply_pattern(talib.CDLBELTHOLD, "CDLBELTHOLD")

    def cdlbreakaway(self) -> pl.LazyFrame:
        """Breakaway."""

        return self._apply_pattern(talib.CDLBREAKAWAY, "CDLBREAKAWAY")

    def cdlclosingmarubozu(self) -> pl.LazyFrame:
        """Closing Marubozu."""

        return self._apply_pattern(talib.CDLCLOSINGMARUBOZU, "CDLCLOSINGMARUBOZU")

    def cdlconcealbabyswall(self) -> pl.LazyFrame:
        """Concealing Baby Swallow."""

        return self._apply_pattern(talib.CDLCONCEALBABYSWALL, "CDLCONCEALBABYSWALL")

    def cdlcounterattack(self) -> pl.LazyFrame:
        """Counterattack."""

        return self._apply_pattern(talib.CDLCOUNTERATTACK, "CDLCOUNTERATTACK")

    def cdldarkcloudcover(self, penetration: float = 0.5) -> pl.LazyFrame:
        """Dark Cloud Cover."""

        return self._apply_pattern(
            talib.CDLDARKCLOUDCOVER, "CDLDARKCLOUDCOVER", penetration=penetration
        )

    def cdldoji(self) -> pl.LazyFrame:
        """Doji."""

        return self._apply_pattern(talib.CDLDOJI, "CDLDOJI")

    def cdldojistar(self) -> pl.LazyFrame:
        """Doji Star."""

        return self._apply_pattern(talib.CDLDOJISTAR, "CDLDOJISTAR")

    def cdldragonflydoji(self) -> pl.LazyFrame:
        """Dragonfly Doji."""

        return self._apply_pattern(talib.CDLDRAGONFLYDOJI, "CDLDRAGONFLYDOJI")

    def cdlengulfing(self) -> pl.LazyFrame:
        """Engulfing Pattern."""

        return self._apply_pattern(talib.CDLENGULFING, "CDLENGULFING")

    def cdleveningdojistar(self, penetration: float = 0.3) -> pl.LazyFrame:
        """Evening Doji Star."""

        return self._apply_pattern(
            talib.CDLEVENINGDOJISTAR,
            "CDLEVENINGDOJISTAR",
            penetration=penetration,
        )

    def cdleveningstar(self, penetration: float = 0.3) -> pl.LazyFrame:
        """Evening Star."""

        return self._apply_pattern(
            talib.CDLEVENINGSTAR, "CDLEVENINGSTAR", penetration=penetration
        )

    def cdlgapsidesidewhite(self) -> pl.LazyFrame:
        """Up/Down-gap side-by-side white lines."""

        return self._apply_pattern(talib.CDLGAPSIDESIDEWHITE, "CDLGAPSIDESIDEWHITE")

    def cdlgravestonedoji(self) -> pl.LazyFrame:
        """Gravestone Doji."""

        return self._apply_pattern(talib.CDLGRAVESTONEDOJI, "CDLGRAVESTONEDOJI")

    def cdlhammer(self) -> pl.LazyFrame:
        """Hammer."""

        return self._apply_pattern(talib.CDLHAMMER, "CDLHAMMER")

    def cdlhangingman(self) -> pl.LazyFrame:
        """Hanging Man."""

        return self._apply_pattern(talib.CDLHANGINGMAN, "CDLHANGINGMAN")

    def cdlharami(self) -> pl.LazyFrame:
        """Harami Pattern."""

        return self._apply_pattern(talib.CDLHARAMI, "CDLHARAMI")

    def cdlharamicross(self) -> pl.LazyFrame:
        """Harami Cross Pattern."""

        return self._apply_pattern(talib.CDLHARAMICROSS, "CDLHARAMICROSS")

    def cdlhighwave(self) -> pl.LazyFrame:
        """High-Wave Candle."""

        return self._apply_pattern(talib.CDLHIGHWAVE, "CDLHIGHWAVE")

    def cdlhikkake(self) -> pl.LazyFrame:
        """Hikkake Pattern."""

        return self._apply_pattern(talib.CDLHIKKAKE, "CDLHIKKAKE")

    def cdlhikkakemod(self) -> pl.LazyFrame:
        """Modified Hikkake Pattern."""

        return self._apply_pattern(talib.CDLHIKKAKEMOD, "CDLHIKKAKEMOD")

    def cdlhomingpigeon(self) -> pl.LazyFrame:
        """Homing Pigeon."""

        return self._apply_pattern(talib.CDLHOMINGPIGEON, "CDLHOMINGPIGEON")

    def cdlidentical3crows(self) -> pl.LazyFrame:
        """Identical Three Crows."""

        return self._apply_pattern(talib.CDLIDENTICAL3CROWS, "CDLIDENTICAL3CROWS")

    def cdlinneck(self) -> pl.LazyFrame:
        """In-Neck Pattern."""

        return self._apply_pattern(talib.CDLINNECK, "CDLINNECK")

    def cdlinvertedhammer(self) -> pl.LazyFrame:
        """Inverted Hammer."""

        return self._apply_pattern(talib.CDLINVERTEDHAMMER, "CDLINVERTEDHAMMER")

    def cdlkicking(self) -> pl.LazyFrame:
        """Kicking."""

        return self._apply_pattern(talib.CDLKICKING, "CDLKICKING")

    def cdlkickingbylength(self) -> pl.LazyFrame:
        """Kicking by length."""

        return self._apply_pattern(talib.CDLKICKINGBYLENGTH, "CDLKICKINGBYLENGTH")

    def cdlladderbottom(self) -> pl.LazyFrame:
        """Ladder Bottom."""

        return self._apply_pattern(talib.CDLLADDERBOTTOM, "CDLLADDERBOTTOM")

    def cdllongleggeddoji(self) -> pl.LazyFrame:
        """Long Legged Doji."""

        return self._apply_pattern(talib.CDLLONGLEGGEDDOJI, "CDLLONGLEGGEDDOJI")

    def cdllongline(self) -> pl.LazyFrame:
        """Long Line Candle."""

        return self._apply_pattern(talib.CDLLONGLINE, "CDLLONGLINE")

    def cdlmarubozu(self) -> pl.LazyFrame:
        """Marubozu."""

        return self._apply_pattern(talib.CDLMARUBOZU, "CDLMARUBOZU")

    def cdlmatchinglow(self) -> pl.LazyFrame:
        """Matching Low."""

        return self._apply_pattern(talib.CDLMATCHINGLOW, "CDLMATCHINGLOW")

    def cdlmathold(self, penetration: float = 0.5) -> pl.LazyFrame:
        """Mat Hold."""

        return self._apply_pattern(
            talib.CDLMATHOLD, "CDLMATHOLD", penetration=penetration
        )

    def cdlmorningdojistar(self, penetration: float = 0.3) -> pl.LazyFrame:
        """Morning Doji Star."""

        return self._apply_pattern(
            talib.CDLMORNINGDOJISTAR,
            "CDLMORNINGDOJISTAR",
            penetration=penetration,
        )

    def cdlmorningstar(self, penetration: float = 0.3) -> pl.LazyFrame:
        """Morning Star."""

        return self._apply_pattern(
            talib.CDLMORNINGSTAR, "CDLMORNINGSTAR", penetration=penetration
        )

    def cdlonneck(self) -> pl.LazyFrame:
        """On-Neck Pattern."""

        return self._apply_pattern(talib.CDLONNECK, "CDLONNECK")

    def cdlpiercing(self) -> pl.LazyFrame:
        """Piercing Pattern."""

        return self._apply_pattern(talib.CDLPIERCING, "CDLPIERCING")

    def cdlrickshawman(self) -> pl.LazyFrame:
        """Rickshaw Man."""

        return self._apply_pattern(talib.CDLRICKSHAWMAN, "CDLRICKSHAWMAN")

    def cdlrisefall3methods(self) -> pl.LazyFrame:
        """Rising/Falling Three Methods."""

        return self._apply_pattern(talib.CDLRISEFALL3METHODS, "CDLRISEFALL3METHODS")

    def cdlseparatinglines(self) -> pl.LazyFrame:
        """Separating Lines."""

        return self._apply_pattern(talib.CDLSEPARATINGLINES, "CDLSEPARATINGLINES")

    def cdlshootingstar(self) -> pl.LazyFrame:
        """Shooting Star."""

        return self._apply_pattern(talib.CDLSHOOTINGSTAR, "CDLSHOOTINGSTAR")

    def cdlshortline(self) -> pl.LazyFrame:
        """Short Line Candle."""

        return self._apply_pattern(talib.CDLSHORTLINE, "CDLSHORTLINE")

    def cdlspinningtop(self) -> pl.LazyFrame:
        """Spinning Top."""

        return self._apply_pattern(talib.CDLSPINNINGTOP, "CDLSPINNINGTOP")

    def cdlstalledpattern(self) -> pl.LazyFrame:
        """Stalled Pattern."""

        return self._apply_pattern(talib.CDLSTALLEDPATTERN, "CDLSTALLEDPATTERN")

    def cdlsticksandwich(self) -> pl.LazyFrame:
        """Stick Sandwich."""

        return self._apply_pattern(talib.CDLSTICKSANDWICH, "CDLSTICKSANDWICH")

    def cdltakuri(self) -> pl.LazyFrame:
        """Takuri."""

        return self._apply_pattern(talib.CDLTAKURI, "CDLTAKURI")

    def cdltasukigap(self) -> pl.LazyFrame:
        """Tasuki Gap."""

        return self._apply_pattern(talib.CDLTASUKIGAP, "CDLTASUKIGAP")

    def cdlthrusting(self) -> pl.LazyFrame:
        """Thrusting Pattern."""

        return self._apply_pattern(talib.CDLTHRUSTING, "CDLTHRUSTING")

    def cdltristar(self) -> pl.LazyFrame:
        """Tristar Pattern."""

        return self._apply_pattern(talib.CDLTRISTAR, "CDLTRISTAR")

    def cdlunique3river(self) -> pl.LazyFrame:
        """Unique 3 River."""

        return self._apply_pattern(talib.CDLUNIQUE3RIVER, "CDLUNIQUE3RIVER")

    def cdlupsidegap2crows(self) -> pl.LazyFrame:
        """Upside Gap Two Crows."""

        return self._apply_pattern(talib.CDLUPSIDEGAP2CROWS, "CDLUPSIDEGAP2CROWS")

    def cdlxsidegap3methods(self) -> pl.LazyFrame:
        """Upside/Downside Gap Three Methods."""

        return self._apply_pattern(talib.CDLXSIDEGAP3METHODS, "CDLXSIDEGAP3METHODS")
