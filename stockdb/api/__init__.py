import logging
import os
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

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

# Setting CONFIG_FILE environment variable if not already set
if config_path := os.getenv("CONFIG_FILE"):
    if not Path(config_path).exists():  # just to verify path exists
        base_dir = Path(__file__).resolve().parent.parent.parent
        default_config_path = base_dir / "config.toml"
        os.environ["CONFIG_FILE"] = default_config_path.resolve().as_posix()
else:
    base_dir = Path(__file__).resolve().parent.parent.parent
    default_config_path = base_dir / "config.toml"
    os.environ["CONFIG_FILE"] = default_config_path.resolve().as_posix()


def setup():
    """Setup function to initialize whereas prerequisite package."""
    # Setting CONFIG_FILE environment variable if not already set
    if config_path := os.getenv("CONFIG_FILE"):
        if not Path(config_path).exists():  # just to verify path exists
            base_dir = Path(__file__).resolve().parent.parent.parent
            default_config_path = base_dir / "config.toml"
            os.environ["CONFIG_FILE"] = default_config_path.resolve().as_posix()
    else:
        base_dir = Path(__file__).resolve().parent.parent.parent
        default_config_path = base_dir / "config.toml"
        os.environ["CONFIG_FILE"] = default_config_path.resolve().as_posix()
