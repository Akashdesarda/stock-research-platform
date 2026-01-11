import os
from pathlib import Path

import pytest
from stocksense import config as cfg


def _write_minimal_config(path: Path) -> None:
    # Minimal file for resolution tests; we don't parse it here.
    path.write_text("[common]\nbase_url='http://localhost'\n")


def test_resolve_config_file_prefers_explicit_argument(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cfg_path = tmp_path / "config.toml"
    _write_minimal_config(cfg_path)

    monkeypatch.delenv("CONFIG_FILE", raising=False)
    monkeypatch.delenv("STOCKSENSE_CONFIG_FILE", raising=False)

    resolved = cfg.resolve_config_file(cfg_path)
    assert resolved == cfg_path.resolve()


def test_resolve_config_file_uses_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cfg_path = tmp_path / "config.toml"
    _write_minimal_config(cfg_path)

    monkeypatch.setenv("CONFIG_FILE", str(cfg_path))
    monkeypatch.delenv("STOCKSENSE_CONFIG_FILE", raising=False)

    resolved = cfg.resolve_config_file(None)
    assert resolved == cfg_path.resolve()


def test_resolve_config_file_falls_back_when_env_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # env points to a missing file; resolver should still find config.toml by searching upwards.
    root = tmp_path / "repo"
    nested = root / "a" / "b" / "c"
    nested.mkdir(parents=True)

    cfg_path = root / "config.toml"
    _write_minimal_config(cfg_path)

    monkeypatch.setenv("CONFIG_FILE", str(root / "does-not-exist.toml"))
    monkeypatch.chdir(nested)

    resolved = cfg.resolve_config_file(None)
    assert resolved == cfg_path.resolve()


def test_resolve_config_file_searches_upwards_from_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "repo"
    nested = root / "sub" / "project"
    nested.mkdir(parents=True)

    cfg_path = root / "config.toml"
    _write_minimal_config(cfg_path)

    monkeypatch.delenv("CONFIG_FILE", raising=False)
    monkeypatch.delenv("STOCKSENSE_CONFIG_FILE", raising=False)
    monkeypatch.chdir(nested)

    resolved = cfg.resolve_config_file(None)
    assert resolved == cfg_path.resolve()


def test_ensure_config_env_sets_CONFIG_FILE(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cfg_path = tmp_path / "config.toml"
    _write_minimal_config(cfg_path)

    monkeypatch.delenv("CONFIG_FILE", raising=False)

    resolved = cfg.ensure_config_env(cfg_path)
    assert resolved == cfg_path.resolve()
    assert os.environ.get("CONFIG_FILE") == str(cfg_path.resolve())


def test_resolve_data_path_translates_docker_mount_locally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Make the target deterministic on Linux using XDG_DATA_HOME.
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    # Ensure local-mode behavior for this test.
    monkeypatch.setattr(cfg, "_is_running_in_docker", lambda: False)

    resolved = cfg._resolve_data_path(Path("/shared/assets/stockdb"))
    assert resolved == (Path(os.environ["XDG_DATA_HOME"]) / "stock-research-platform")
    assert resolved.exists()
