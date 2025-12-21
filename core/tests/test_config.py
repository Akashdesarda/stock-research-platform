import contextlib
import os
from pathlib import Path

from stocksense.config import get_settings


class Common:
    pass


class App:
    pass


class StockDB:
    pass


def test_env_variable_config_file():
    _ = Path(__file__).parent.parent.parent / "config.toml"
    os.environ["CONFIG_FILE"] = _.resolve().as_posix()
    settings = get_settings()
    assert settings.common.base_url == "http://localhost"
    assert settings.app.port == 4000
    assert settings.stockdb.download_batch_size == 50


def test_direct_config_file():
    settings = get_settings(
        config_path=Path(__file__).parent.parent.parent / "config.toml"
    )

    assert settings.common.base_url == "http://localhost"
    assert settings.app.port == 4000
    assert settings.stockdb.download_batch_size == 50


def test_no_config_file():
    with contextlib.suppress(KeyError):
        os.environ.pop("CONFIG_FILE")
    try:
        get_settings()
    except ValueError as e:
        assert str(e) == "No configuration file path provided."
