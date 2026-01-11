import os
import platform
from pathlib import Path
from typing import Annotated, Iterable

from pydantic import AfterValidator, BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def _is_running_in_docker() -> bool:
    """Check if the application is running inside a Docker container."""
    # NOTE: Do NOT use CONFIG_FILE.startswith("/") as a Docker signal.
    # On Linux/macOS local machines, absolute paths also start with "/".
    if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true":
        return True

    # Best-effort heuristic using cgroups (works in many Docker/K8s setups).
    try:
        cgroup = Path("/proc/1/cgroup")
        if cgroup.exists():
            txt = cgroup.read_text(errors="ignore")
            if "docker" in txt or "kubepods" in txt or "containerd" in txt:
                return True
    except OSError:
        pass

    return False


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


def _resolve_data_path(config_path: Path) -> Path:
    """
    Resolve the data path based on the environment.
    - In Docker: use the path as-is (mounted volume path)
    - On local machine: translate Docker path to appropriate OS-specific path
    """
    if _is_running_in_docker():
        return config_path

    # Running locally - translate Docker paths to local OS-appropriate paths
    elif config_path.as_posix().startswith("/shared/assets/stockdb"):
        # This is the Docker mount target, translate to local data directory
        resolved_path = _get_local_data_directory()
        # Ensure the directory exists
        resolved_path.mkdir(parents=True, exist_ok=True)
        return resolved_path

    else:
        # If it's already a local path, use as-is
        return config_path


def _iter_candidate_roots() -> Iterable[Path]:
    """
    Yield directories to search for config.toml, in priority order.
    """
    # 1) Current working directory (common in monorepos when running from subproject)
    yield Path.cwd()

    # 2) This module's directory (helps when running code via installed package or unusual CWD)
    yield Path(__file__).resolve().parent


def resolve_config_file(
    config_path: str | Path | None = None,
    *,
    filename: str = "config.toml",
) -> Path:
    """
    Resolve a usable config.toml path.

    Resolution order:
    1) explicit argument
    2) env vars (CONFIG_FILE, STOCKSENSE_CONFIG_FILE)
    3) search upwards from common roots (cwd, this module)
    """
    # 1) explicit argument
    if config_path:
        p = Path(config_path).expanduser()
        if p.is_file():
            return p.resolve()
        raise FileNotFoundError(f"Config file not found at: {p}")

    # 2) environment variables
    for env_name in ("CONFIG_FILE", "STOCKSENSE_CONFIG_FILE"):
        raw = os.getenv(env_name)
        if not raw:
            continue
        p = Path(raw).expanduser()
        if p.is_file():
            return p.resolve()
        # If env var is set but invalid, continue to fallback search.

    # 3) upward search
    for root in _iter_candidate_roots():
        root = root.resolve()
        for d in (root, *root.parents):
            candidate = d / filename
            if candidate.is_file():
                return candidate.resolve()

    raise ValueError(
        "No configuration file path provided and config.toml was not found.\n"
        "Tried: argument, env (CONFIG_FILE/STOCKSENSE_CONFIG_FILE), and searching parent dirs.\n"
        "Fix: set CONFIG_FILE=/abs/path/to/config.toml (or run from repo so it can be discovered)."
    )


def ensure_config_env(config_path: str | Path | None = None) -> Path:
    """
    Ensure CONFIG_FILE is set to a valid, existing config.toml path.
    Returns the resolved path.
    """
    resolved = resolve_config_file(config_path)
    os.environ["CONFIG_FILE"] = resolved.as_posix()
    return resolved


# Model for the 'common' section
class Common(BaseModel):
    base_url: str
    available_llm_providers: list[str]
    GROQ_API_KEY: str
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    OLLAMA_API_KEY: str
    GOOGLE_API_KEY: str
    mlflow_port: int


# Model for the 'App' section
class App(BaseModel):
    port: int
    text_to_sql_model: str
    company_summary_model: str
    company_summary_qa_model: str


# StockDB model for the 'stockdb' section
class StockDB(BaseModel):
    port: int
    data_base_path: Annotated[Path, AfterValidator(_resolve_data_path)]
    download_batch_size: int


class Settings(BaseSettings):
    common: Common
    app: App
    stockdb: StockDB

    model_config = SettingsConfigDict()

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

    def save_as_toml(self) -> None:
        """Save the current settings to a TOML file."""
        import toml

        _file = self.model_config.get("toml_file")
        with open(_file, "w") as f:
            toml.dump(self.model_dump(), f)


# the Settings model
def get_settings(config_path: str | Path | None = None) -> Settings:
    """Get the application settings (robust: does not require CONFIG_FILE pre-set)."""
    resolved = ensure_config_env(config_path)

    # set toml file path for Settings before instantiation so BaseSettings reads it
    Settings.model_config["toml_file"] = resolved.as_posix()

    return Settings()  # pyright: ignore[reportCallIssue]  # ty:ignore[missing-argument]
