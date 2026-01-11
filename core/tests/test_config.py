import contextlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from stocksense.config import get_settings


def test_env_variable_config_file():
    _ = Path(__file__).parent.parent.parent / "config.toml"
    os.environ["CONFIG_FILE"] = _.resolve().as_posix()
    settings = get_settings()
    assert settings.common.base_url == "http://localhost"
    assert settings.app.port == 3000
    assert settings.stockdb.download_batch_size == 50


def test_direct_config_file():
    settings = get_settings(
        config_path=Path(__file__).parent.parent.parent / "config.toml"
    )

    assert settings.common.base_url == "http://localhost"
    assert settings.app.port == 3000
    assert settings.stockdb.download_batch_size == 50


def test_no_config_file():
    with contextlib.suppress(KeyError):
        os.environ.pop("CONFIG_FILE")
    try:
        get_settings()
    except ValueError as e:
        assert "No configuration file path provided" in str(e)


def test_config_values():
    settings = get_settings(
        config_path=Path(__file__).parent.parent.parent / "config.toml"
    )

    truth_llm = settings.common.available_llm_providers
    check_llm = [
        "openai",
        "groq",
        "anthropic",
        "google-gla",
        "ollama",
    ]
    truth_llm.sort()
    check_llm.sort()
    assert truth_llm == check_llm
    assert settings.stockdb.port == 8080
    assert settings.app.port == 3000


def test_save_as_toml():
    settings = get_settings(
        config_path=Path(__file__).parent.parent.parent / "config.toml"
    )

    with TemporaryDirectory() as temp_dir:
        temp_config_file = Path(temp_dir) / "temp_config.toml"
        settings.common.OLLAMA_API_KEY = "new_ollama_key"
        settings.common.OPENAI_API_KEY = "new_openai_key"

        settings.model_config["toml_file"] = temp_config_file.resolve().as_posix()
        settings.save_as_toml()

        # Read back the saved file and verify contents
        saved_settings = get_settings(config_path=temp_config_file)
        assert saved_settings.common.OLLAMA_API_KEY == "new_ollama_key"
        assert saved_settings.common.OPENAI_API_KEY == "new_openai_key"
