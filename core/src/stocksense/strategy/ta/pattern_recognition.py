from dataclasses import dataclass

import polars as pl
import talib

from stocksense.strategy.ta import BaseAccessor


@dataclass
class PatternRecognitionAccessor(BaseAccessor):
    """Accessor for candlestick pattern recognition indicators."""

    def _apply_pattern(self, func, name: str, **kwargs) -> pl.DataFrame:
        def calculate(open, high, low, close):
            values = func(open, high, low, close, **kwargs)
            return [pl.Series(name, values)]

        return self._apply_to_groups(["open", "high", "low", "close"], calculate)

    def cdl2crows(self) -> pl.DataFrame:
        """Two Crows."""

        return self._apply_pattern(talib.CDL2CROWS, "CDL2CROWS")

    def cdl3blackcrows(self) -> pl.DataFrame:
        """Three Black Crows."""

        return self._apply_pattern(talib.CDL3BLACKCROWS, "CDL3BLACKCROWS")

    def cdl3inside(self) -> pl.DataFrame:
        """Three Inside Up/Down."""

        return self._apply_pattern(talib.CDL3INSIDE, "CDL3INSIDE")

    def cdl3linestrike(self) -> pl.DataFrame:
        """Three-Line Strike."""

        return self._apply_pattern(talib.CDL3LINESTRIKE, "CDL3LINESTRIKE")

    def cdl3outside(self) -> pl.DataFrame:
        """Three Outside Up/Down."""

        return self._apply_pattern(talib.CDL3OUTSIDE, "CDL3OUTSIDE")

    def cdl3starsinsouth(self) -> pl.DataFrame:
        """Three Stars In The South."""

        return self._apply_pattern(talib.CDL3STARSINSOUTH, "CDL3STARSINSOUTH")

    def cdl3whitesoldiers(self) -> pl.DataFrame:
        """Three Advancing White Soldiers."""

        return self._apply_pattern(talib.CDL3WHITESOLDIERS, "CDL3WHITESOLDIERS")

    def cdlabandonedbaby(self, penetration: float = 0.3) -> pl.DataFrame:
        """Abandoned Baby."""

        return self._apply_pattern(
            talib.CDLABANDONEDBABY, "CDLABANDONEDBABY", penetration=penetration
        )

    def cdladvanceblock(self) -> pl.DataFrame:
        """Advance Block."""

        return self._apply_pattern(talib.CDLADVANCEBLOCK, "CDLADVANCEBLOCK")

    def cdlbelthold(self) -> pl.DataFrame:
        """Belt-hold."""

        return self._apply_pattern(talib.CDLBELTHOLD, "CDLBELTHOLD")

    def cdlbreakaway(self) -> pl.DataFrame:
        """Breakaway."""

        return self._apply_pattern(talib.CDLBREAKAWAY, "CDLBREAKAWAY")

    def cdlclosingmarubozu(self) -> pl.DataFrame:
        """Closing Marubozu."""

        return self._apply_pattern(talib.CDLCLOSINGMARUBOZU, "CDLCLOSINGMARUBOZU")

    def cdlconcealbabyswall(self) -> pl.DataFrame:
        """Concealing Baby Swallow."""

        return self._apply_pattern(talib.CDLCONCEALBABYSWALL, "CDLCONCEALBABYSWALL")

    def cdlcounterattack(self) -> pl.DataFrame:
        """Counterattack."""

        return self._apply_pattern(talib.CDLCOUNTERATTACK, "CDLCOUNTERATTACK")

    def cdldarkcloudcover(self, penetration: float = 0.5) -> pl.DataFrame:
        """Dark Cloud Cover."""

        return self._apply_pattern(
            talib.CDLDARKCLOUDCOVER,
            "CDLDARKCLOUDCOVER",
            penetration=penetration,
        )

    def cdldoji(self) -> pl.DataFrame:
        """Doji."""

        return self._apply_pattern(talib.CDLDOJI, "CDLDOJI")

    def cdldojistar(self) -> pl.DataFrame:
        """Doji Star."""

        return self._apply_pattern(talib.CDLDOJISTAR, "CDLDOJISTAR")

    def cdldragonflydoji(self) -> pl.DataFrame:
        """Dragonfly Doji."""

        return self._apply_pattern(talib.CDLDRAGONFLYDOJI, "CDLDRAGONFLYDOJI")

    def cdlengulfing(self) -> pl.DataFrame:
        """Engulfing Pattern."""

        return self._apply_pattern(talib.CDLENGULFING, "CDLENGULFING")

    def cdleveningdojistar(self, penetration: float = 0.3) -> pl.DataFrame:
        """Evening Doji Star."""

        return self._apply_pattern(
            talib.CDLEVENINGDOJISTAR,
            "CDLEVENINGDOJISTAR",
            penetration=penetration,
        )

    def cdleveningstar(self, penetration: float = 0.3) -> pl.DataFrame:
        """Evening Star."""

        return self._apply_pattern(
            talib.CDLEVENINGSTAR, "CDLEVENINGSTAR", penetration=penetration
        )

    def cdlgapsidesidewhite(self) -> pl.DataFrame:
        """Up/Down-gap side-by-side white lines."""

        return self._apply_pattern(talib.CDLGAPSIDESIDEWHITE, "CDLGAPSIDESIDEWHITE")

    def cdlgravestonedoji(self) -> pl.DataFrame:
        """Gravestone Doji."""

        return self._apply_pattern(talib.CDLGRAVESTONEDOJI, "CDLGRAVESTONEDOJI")

    def cdlhammer(self) -> pl.DataFrame:
        """Hammer."""

        return self._apply_pattern(talib.CDLHAMMER, "CDLHAMMER")

    def cdlhangingman(self) -> pl.DataFrame:
        """Hanging Man."""

        return self._apply_pattern(talib.CDLHANGINGMAN, "CDLHANGINGMAN")

    def cdlharami(self) -> pl.DataFrame:
        """Harami Pattern."""

        return self._apply_pattern(talib.CDLHARAMI, "CDLHARAMI")

    def cdlharamicross(self) -> pl.DataFrame:
        """Harami Cross Pattern."""

        return self._apply_pattern(talib.CDLHARAMICROSS, "CDLHARAMICROSS")

    def cdlhighwave(self) -> pl.DataFrame:
        """High-Wave Candle."""

        return self._apply_pattern(talib.CDLHIGHWAVE, "CDLHIGHWAVE")

    def cdlhikkake(self) -> pl.DataFrame:
        """Hikkake Pattern."""

        return self._apply_pattern(talib.CDLHIKKAKE, "CDLHIKKAKE")

    def cdlhikkakemod(self) -> pl.DataFrame:
        """Modified Hikkake Pattern."""

        return self._apply_pattern(talib.CDLHIKKAKEMOD, "CDLHIKKAKEMOD")

    def cdlhomingpigeon(self) -> pl.DataFrame:
        """Homing Pigeon."""

        return self._apply_pattern(talib.CDLHOMINGPIGEON, "CDLHOMINGPIGEON")

    def cdlidentical3crows(self) -> pl.DataFrame:
        """Identical Three Crows."""

        return self._apply_pattern(talib.CDLIDENTICAL3CROWS, "CDLIDENTICAL3CROWS")

    def cdlinneck(self) -> pl.DataFrame:
        """In-Neck Pattern."""

        return self._apply_pattern(talib.CDLINNECK, "CDLINNECK")

    def cdlinvertedhammer(self) -> pl.DataFrame:
        """Inverted Hammer."""

        return self._apply_pattern(talib.CDLINVERTEDHAMMER, "CDLINVERTEDHAMMER")

    def cdlkicking(self) -> pl.DataFrame:
        """Kicking."""

        return self._apply_pattern(talib.CDLKICKING, "CDLKICKING")

    def cdlkickingbylength(self) -> pl.DataFrame:
        """Kicking by length."""

        return self._apply_pattern(talib.CDLKICKINGBYLENGTH, "CDLKICKINGBYLENGTH")

    def cdlladderbottom(self) -> pl.DataFrame:
        """Ladder Bottom."""

        return self._apply_pattern(talib.CDLLADDERBOTTOM, "CDLLADDERBOTTOM")

    def cdllongleggeddoji(self) -> pl.DataFrame:
        """Long Legged Doji."""

        return self._apply_pattern(talib.CDLLONGLEGGEDDOJI, "CDLLONGLEGGEDDOJI")

    def cdllongline(self) -> pl.DataFrame:
        """Long Line Candle."""

        return self._apply_pattern(talib.CDLLONGLINE, "CDLLONGLINE")

    def cdlmarubozu(self) -> pl.DataFrame:
        """Marubozu."""

        return self._apply_pattern(talib.CDLMARUBOZU, "CDLMARUBOZU")

    def cdlmatchinglow(self) -> pl.DataFrame:
        """Matching Low."""

        return self._apply_pattern(talib.CDLMATCHINGLOW, "CDLMATCHINGLOW")

    def cdlmathold(self, penetration: float = 0.5) -> pl.DataFrame:
        """Mat Hold."""

        return self._apply_pattern(
            talib.CDLMATHOLD, "CDLMATHOLD", penetration=penetration
        )

    def cdlmorningdojistar(self, penetration: float = 0.3) -> pl.DataFrame:
        """Morning Doji Star."""

        return self._apply_pattern(
            talib.CDLMORNINGDOJISTAR,
            "CDLMORNINGDOJISTAR",
            penetration=penetration,
        )

    def cdlmorningstar(self, penetration: float = 0.3) -> pl.DataFrame:
        """Morning Star."""

        return self._apply_pattern(
            talib.CDLMORNINGSTAR, "CDLMORNINGSTAR", penetration=penetration
        )

    def cdlonneck(self) -> pl.DataFrame:
        """On-Neck Pattern."""

        return self._apply_pattern(talib.CDLONNECK, "CDLONNECK")

    def cdlpiercing(self) -> pl.DataFrame:
        """Piercing Pattern."""

        return self._apply_pattern(talib.CDLPIERCING, "CDLPIERCING")

    def cdlrickshawman(self) -> pl.DataFrame:
        """Rickshaw Man."""

        return self._apply_pattern(talib.CDLRICKSHAWMAN, "CDLRICKSHAWMAN")

    def cdlrisefall3methods(self) -> pl.DataFrame:
        """Rising/Falling Three Methods."""

        return self._apply_pattern(talib.CDLRISEFALL3METHODS, "CDLRISEFALL3METHODS")

    def cdlseparatinglines(self) -> pl.DataFrame:
        """Separating Lines."""

        return self._apply_pattern(talib.CDLSEPARATINGLINES, "CDLSEPARATINGLINES")

    def cdlshootingstar(self) -> pl.DataFrame:
        """Shooting Star."""

        return self._apply_pattern(talib.CDLSHOOTINGSTAR, "CDLSHOOTINGSTAR")

    def cdlshortline(self) -> pl.DataFrame:
        """Short Line Candle."""

        return self._apply_pattern(talib.CDLSHORTLINE, "CDLSHORTLINE")

    def cdlspinningtop(self) -> pl.DataFrame:
        """Spinning Top."""

        return self._apply_pattern(talib.CDLSPINNINGTOP, "CDLSPINNINGTOP")

    def cdlstalledpattern(self) -> pl.DataFrame:
        """Stalled Pattern."""

        return self._apply_pattern(talib.CDLSTALLEDPATTERN, "CDLSTALLEDPATTERN")

    def cdlsticksandwich(self) -> pl.DataFrame:
        """Stick Sandwich."""

        return self._apply_pattern(talib.CDLSTICKSANDWICH, "CDLSTICKSANDWICH")

    def cdltakuri(self) -> pl.DataFrame:
        """Takuri."""

        return self._apply_pattern(talib.CDLTAKURI, "CDLTAKURI")

    def cdltasukigap(self) -> pl.DataFrame:
        """Tasuki Gap."""

        return self._apply_pattern(talib.CDLTASUKIGAP, "CDLTASUKIGAP")

    def cdlthrusting(self) -> pl.DataFrame:
        """Thrusting Pattern."""

        return self._apply_pattern(talib.CDLTHRUSTING, "CDLTHRUSTING")

    def cdltristar(self) -> pl.DataFrame:
        """Tristar Pattern."""

        return self._apply_pattern(talib.CDLTRISTAR, "CDLTRISTAR")

    def cdlunique3river(self) -> pl.DataFrame:
        """Unique 3 River."""

        return self._apply_pattern(talib.CDLUNIQUE3RIVER, "CDLUNIQUE3RIVER")

    def cdlupsidegap2crows(self) -> pl.DataFrame:
        """Upside Gap Two Crows."""

        return self._apply_pattern(talib.CDLUPSIDEGAP2CROWS, "CDLUPSIDEGAP2CROWS")

    def cdlxsidegap3methods(self) -> pl.DataFrame:
        """Upside/Downside Gap Three Methods."""

        return self._apply_pattern(talib.CDLXSIDEGAP3METHODS, "CDLXSIDEGAP3METHODS")
