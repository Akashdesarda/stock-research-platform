from __future__ import annotations

from enum import Enum


class ExchangeChoice(str, Enum):
    """Small demo enum for dropdowns.

    Using `str, Enum` keeps values JSON-friendly for Reflex state.
    """

    nse = "NSE"
    bse = "BSE"
    nasdaq = "NASDAQ"
