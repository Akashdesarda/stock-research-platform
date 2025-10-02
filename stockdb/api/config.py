import os
from pathlib import Path

from pydantic import BaseModel
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


# StockDB model for the 'stockdb' section
class StockDB(BaseModel):
    data_base_path: DirectoryPath
    download_batch_size: int


# the Settings model
class Settings(BaseSettings):
    stockdb: StockDB

    model_config = SettingsConfigDict(
        toml_file=config_path,
        # env_nested_delimiter=None,  # Ensure nested keys are handled correctly
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
