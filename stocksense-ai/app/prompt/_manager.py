import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, Undefined

logger = logging.getLogger("stocksense")


@dataclass
class PromptManager:
    strict_templates: bool = True

    def __post_init__(self) -> None:
        self._prompt_dir = Path(__file__).parent
        self._prompt_registry = {}
        self._jinja_env = Environment(
            undefined=StrictUndefined if self.strict_templates else Undefined
        )
        self._load_all_prompts()

    def _load_all_prompts(self) -> None:
        """Eagerly load all YAML prompt files from the prompt directory."""
        self._prompt_registry.clear()

        for file_path in self._prompt_dir.glob("*.yaml"):
            agent_name = file_path.stem
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    prompts = yaml.safe_load(f) or {}

                if not isinstance(prompts, dict):
                    logger.error(
                        f"Prompt file for agent {agent_name} must contain a YAML mapping at root. Got: {type(prompts).__name__}"
                    )
                    self._prompt_registry[agent_name] = {}
                    continue

                if "versions" in prompts:
                    versioned = {}
                    versions_dict = prompts.get("versions") or {}
                    default_version = prompts.get("default_version", next(iter(versions_dict), None))
                    if default_version is not None:
                        versioned["_default_version"] = default_version
                    versioned["_versions"] = versions_dict
                    self._prompt_registry[agent_name] = versioned
                else:
                    self._prompt_registry[agent_name] = prompts
            except Exception:
                logger.exception(
                    f"Error loading prompts for agent {agent_name} from {file_path}"
                )
                self._prompt_registry[agent_name] = {}

    def _resolve_prompts(self, agent_name: str, version: str | None = None) -> dict[str, Any]:
        prompts = self._prompt_registry.get(agent_name, {})
        if not prompts:
            raise ValueError(f"Agent not found: {agent_name}")

        if version is not None:
            versions = prompts.get("_versions", {})
            if version not in versions:
                raise ValueError(
                    f"Version '{version}' not found for agent '{agent_name}'. "
                    f"Available: {sorted(versions.keys()) or 'none (not a versioned agent)'}"
                )
            return versions[version]

        if "_versions" in prompts:
            default_version = prompts.get("_default_version")
            if default_version is None:
                raise ValueError(
                    f"No default_version configured for versioned agent '{agent_name}'"
                )
            versions = prompts["_versions"]
            if default_version not in versions:
                raise ValueError(
                    f"Default version '{default_version}' not found for agent '{agent_name}'. "
                    f"Available: {sorted(versions.keys())}"
                )
            return versions[default_version]

        return prompts

    def get_prompt(
        self, agent_name: str, prompt_key: str, version: str | None = None, **kwargs: Any
    ) -> str:
        """
        Retrieves a prompt and renders it with the provided keyword arguments.

        For versioned prompt files, pass `version` to select a specific version.
        If `version` is omitted, the default version is used for versioned agents,
        or the flat prompt is returned for non-versioned agents.
        """
        prompts = self._resolve_prompts(agent_name, version)
        template_str = prompts.get(prompt_key, "")
        if not isinstance(template_str, str) or not template_str:
            raise ValueError(
                f"Prompt not found: {agent_name}.{prompt_key}"
                + (f" (version={version})" if version else "")
            )

        template = self._jinja_env.from_string(template_str)
        return template.render(**kwargs)

    def get_available_versions(self, agent_name: str) -> list[str]:
        """Return available versions for an agent, or an empty list if not versioned."""
        prompts = self._prompt_registry.get(agent_name, {})
        versions = prompts.get("_versions", {})
        return sorted(versions.keys())

    def clear_cache(self, agent_name: str | None = None) -> None:
        if agent_name is None:
            self._prompt_registry.clear()
        else:
            self._prompt_registry.pop(agent_name, None)

    def reload(self) -> None:
        """Reload all prompt YAML files from disk."""
        self._load_all_prompts()
