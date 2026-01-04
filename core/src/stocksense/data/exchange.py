from dataclasses import dataclass

from ._nse import NSEAccessor


@dataclass
class Exchange:
    name: str

    @property
    def nse(self) -> NSEAccessor:
        """NSE (National Stock Exchange of India) data accessor."""
        if self.name.lower() != "nse":
            raise ValueError("NSE accessor is only available for NSE exchange.")
        return NSEAccessor()
