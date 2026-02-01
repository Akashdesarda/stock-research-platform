from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._nse import NSEAccessor


@dataclass
class Exchange:
    @property
    def nse(self) -> "NSEAccessor":
        """NSE (National Stock Exchange of India) data accessor."""
        from ._nse import NSEAccessor

        return NSEAccessor()
