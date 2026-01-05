from dataclasses import dataclass

from ._nse import NSEAccessor


@dataclass
class Exchange:
    @property
    def nse(self) -> NSEAccessor:
        """NSE (National Stock Exchange of India) data accessor."""
        return NSEAccessor()
