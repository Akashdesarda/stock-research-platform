import logging

from rich.console import Console
from rich.logging import RichHandler
from stocksense.config import ensure_config_env

logger = logging.getLogger("stockdb")
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


def setup():
    """Ensure that the configuration environment is set up for stockdb"""
    ensure_config_env()
