import os
from pathlib import Path


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
