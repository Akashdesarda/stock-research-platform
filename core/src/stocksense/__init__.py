import logging

from rich.console import Console
from rich.logging import RichHandler

logger = logging.getLogger("stocksense")
console_handler = RichHandler(
    markup=True,
    show_path=False,
    console=Console(),
    locals_max_string=150,
)
log_format = logging.Formatter("%(message)s", datefmt="%d-%b-%y %H:%M:%S")
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)

__version__ = "0.3.0"
