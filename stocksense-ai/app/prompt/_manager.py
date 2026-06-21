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
                    prompts = {}

                self._prompt_registry[agent_name] = prompts
            except Exception:
                logger.exception(
                    f"Error loading prompts for agent {agent_name} from {file_path}"
                )
                self._prompt_registry[agent_name] = {}

    def get_prompt(self, agent_name: str, prompt_key: str, **kwargs: Any) -> str:
        """
        Retrieves a prompt and renders it with the provided keyword arguments.
        """
        prompts = self._prompt_registry.get(agent_name, {})
        template_str = prompts.get(prompt_key, "")
        if not isinstance(template_str, str) or not template_str:
            raise ValueError(f"Prompt not found: {agent_name}.{prompt_key}")

        template = self._jinja_env.from_string(template_str)
        return template.render(**kwargs)

    def clear_cache(self, agent_name: str | None = None) -> None:
        if agent_name is None:
            self._prompt_registry.clear()
        else:
            self._prompt_registry.pop(agent_name, None)

    def reload(self) -> None:
        """Reload all prompt YAML files from disk."""
        self._load_all_prompts()
