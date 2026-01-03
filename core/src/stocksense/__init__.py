import logging
import os
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

__version__ = "0.5.0"

# Setting logging
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


# Setting CONFIG_FILE environment variable if not already set
base_dir = Path(__file__).resolve().parent.parent.parent.parent
default_config_path = base_dir / "config.toml"
os.environ.setdefault("CONFIG_FILE", default_config_path.resolve().as_posix())
