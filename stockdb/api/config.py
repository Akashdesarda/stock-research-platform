import os
import platform
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic.types import DirectoryPath
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

# Define the default config path
default_config_path = Path(__file__).parent.parent.parent / "config.toml"
config_path = Path(os.getenv("CONFIG_FILE", default_config_path.resolve().as_posix()))


def _is_running_in_docker() -> bool:
    """Check if the application is running inside a Docker container."""
    return (
        os.path.exists("/.dockerenv")
        or os.getenv("DOCKER_CONTAINER") == "true"
        or os.getenv("CONFIG_FILE", "").startswith("/")
    )


def _get_local_data_directory() -> Path:
    """
    Get the appropriate local data directory based on the operating system.
    Returns a cross-platform data directory following OS conventions.
    """
    system = platform.system().lower()

    if system == "windows":
        # Windows: Use AppData/Roaming
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "darwin":  # macOS
        # macOS: Use ~/Library/Application Support
        base_dir = Path.home() / "Library" / "Application Support"
    else:  # Linux and other Unix-like systems
        # Linux: Use XDG_DATA_HOME or ~/.local/share
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base_dir = Path(xdg_data_home)
        else:
            base_dir = Path.home() / ".local" / "share"

    return base_dir / "stock-research-platform"


def _resolve_data_path(config_path: str) -> Path:
    """
    Resolve the data path based on the environment.
    - In Docker: use the path as-is (mounted volume path)
    - On local machine: translate Docker path to appropriate OS-specific path
    """
    if _is_running_in_docker():
        return Path(config_path)

    # Running locally - translate Docker paths to local OS-appropriate paths
    if config_path.startswith("/shared/assets/stockdb"):
        # This is the Docker mount target, translate to local data directory
        resolved_path = _get_local_data_directory()
        # Ensure the directory exists
        resolved_path.mkdir(parents=True, exist_ok=True)
        return resolved_path

    # If it's already a local path, use as-is
    return Path(config_path)


# Model for the 'common' section
class Common(BaseModel):
    base_url: str


# Model for the 'App' section
class App(BaseModel):
    port: int


# StockDB model for the 'stockdb' section
class StockDB(BaseModel):
    port: int
    data_base_path: Annotated[str | DirectoryPath, AfterValidator(_resolve_data_path)]
    download_batch_size: int


# the Settings model
class Settings(BaseSettings):
    common: Common
    app: App
    stockdb: StockDB

    model_config = SettingsConfigDict(
        toml_file=config_path,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)
