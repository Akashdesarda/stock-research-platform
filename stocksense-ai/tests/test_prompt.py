import pytest
from pathlib import Path
from app.prompt import PromptManager
from jinja2 import UndefinedError


@pytest.fixture
def prompt_manager(tmp_path):
    """Fixture to initialize PromptManager with a temporary directory for testing."""
    manager = PromptManager(strict_templates=True)
    manager._prompt_dir = tmp_path
    return manager


def test_load_all_prompts_empty_directory(prompt_manager):
    """Test loading prompts when the directory is empty."""
    prompt_manager._load_all_prompts()
    assert prompt_manager._prompt_registry == {}


def test_load_valid_yaml_prompts(prompt_manager, tmp_path):
    """Test loading valid YAML prompts."""
    test_file = tmp_path / "example.yaml"
    test_file.write_text(
        """
        example_key: |
          Test prompt for {{ name }}.
        """
    )

    prompt_manager._load_all_prompts()
    assert "example" in prompt_manager._prompt_registry
    assert "example_key" in prompt_manager._prompt_registry["example"]


def test_load_invalid_yaml_prompt(prompt_manager, tmp_path, caplog):
    """Test loading an invalid YAML prompt."""
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text("just a plain string")

    prompt_manager._load_all_prompts()

    assert "invalid" in prompt_manager._prompt_registry
    assert prompt_manager._prompt_registry["invalid"] == {}
    assert "must contain a YAML mapping" in caplog.text


def test_get_prompt_valid_key(prompt_manager, tmp_path):
    """Test retrieving and rendering a valid prompt."""
    test_file = tmp_path / "example.yaml"
    test_file.write_text(
        """
        example_key: |
          Test prompt for {{ name }}.
        """
    )
    prompt_manager._load_all_prompts()

    result = prompt_manager.get_prompt("example", "example_key", name="John")
    assert result == "Test prompt for John."


def test_get_prompt_missing_key(prompt_manager, tmp_path):
    """Test retrieving a prompt with a missing key."""
    test_file = tmp_path / "example.yaml"
    test_file.write_text(
        """
        another_key: |
          Another prompt.
        """
    )
    prompt_manager._load_all_prompts()

    with pytest.raises(ValueError, match="Prompt not found: example.missing_key"):
        prompt_manager.get_prompt("example", "missing_key")


def test_get_prompt_invalid_template(prompt_manager, tmp_path):
    """Test rendering a prompt with an invalid template."""
    test_file = tmp_path / "example.yaml"
    test_file.write_text(
        """
        example_key: |
          Test prompt for {{ invalid_variable }}.
        """
    )
    prompt_manager._load_all_prompts()

    with pytest.raises(UndefinedError, match="invalid_variable"):
        prompt_manager.get_prompt("example", "example_key")


def test_clear_cache_all(prompt_manager, tmp_path):
    """Test clearing all cache."""
    test_file = tmp_path / "example.yaml"
    test_file.write_text(
        """
        example_key: |
          Test prompt.
        """
    )
    prompt_manager._load_all_prompts()
    assert "example" in prompt_manager._prompt_registry

    prompt_manager.clear_cache()
    assert prompt_manager._prompt_registry == {}


def test_clear_cache_single_agent(prompt_manager, tmp_path):
    """Test clearing cache for a single agent."""
    test_file_1 = tmp_path / "agent1.yaml"
    test_file_2 = tmp_path / "agent2.yaml"

    test_file_1.write_text(
        """
        key1: |
          Agent 1 prompt.
        """
    )
    test_file_2.write_text(
        """
        key2: |
          Agent 2 prompt.
        """
    )

    prompt_manager._load_all_prompts()
    assert "agent1" in prompt_manager._prompt_registry
    assert "agent2" in prompt_manager._prompt_registry

    prompt_manager.clear_cache("agent1")
    assert "agent1" not in prompt_manager._prompt_registry
    assert "agent2" in prompt_manager._prompt_registry


def test_reload_prompts(prompt_manager, tmp_path):
    """Test reloading prompts."""
    test_file = tmp_path / "reload_test.yaml"
    test_file.write_text(
        """
        initial_key: |
          Initial prompt.
        """
    )
    prompt_manager._load_all_prompts()
    assert "reload_test" in prompt_manager._prompt_registry
    assert "initial_key" in prompt_manager._prompt_registry["reload_test"]

    # Update the file
    test_file.write_text(
        """
        updated_key: |
          Updated prompt.
        """
    )
    prompt_manager.reload()
    assert "initial_key" not in prompt_manager._prompt_registry["reload_test"]
    assert "updated_key" in prompt_manager._prompt_registry["reload_test"]


def test_load_versioned_prompts(prompt_manager, tmp_path):
    """Test loading versioned YAML prompts."""
    test_file = tmp_path / "versioned.yaml"
    test_file.write_text(
        """
        default_version: v2
        versions:
          v1:
            welcome: |
              Hello {{ name }} (v1).
          v2:
            welcome: |
              Hello {{ name }} (v2).
        """
    )
    prompt_manager._load_all_prompts()
    assert "versioned" in prompt_manager._prompt_registry
    assert "_versions" in prompt_manager._prompt_registry["versioned"]
    assert "_default_version" in prompt_manager._prompt_registry["versioned"]


def test_get_prompt_default_version(prompt_manager, tmp_path):
    """Test retrieving prompt from default version when no version is specified."""
    test_file = tmp_path / "versioned.yaml"
    test_file.write_text(
        """
        default_version: v2
        versions:
          v1:
            welcome: |
              Hello {{ name }} (v1).
          v2:
            welcome: |
              Hello {{ name }} (v2).
        """
    )
    prompt_manager._load_all_prompts()
    result = prompt_manager.get_prompt("versioned", "welcome", name="World")
    assert result == "Hello World (v2)."


def test_get_prompt_specific_version(prompt_manager, tmp_path):
    """Test retrieving prompt from a specific version."""
    test_file = tmp_path / "versioned.yaml"
    test_file.write_text(
        """
        default_version: v2
        versions:
          v1:
            welcome: |
              Hello {{ name }} (v1).
          v2:
            welcome: |
              Hello {{ name }} (v2).
        """
    )
    prompt_manager._load_all_prompts()
    result = prompt_manager.get_prompt("versioned", "welcome", version="v1", name="World")
    assert result == "Hello World (v1)."


def test_get_prompt_missing_version(prompt_manager, tmp_path):
    """Test error when requesting a non-existent version."""
    test_file = tmp_path / "versioned.yaml"
    test_file.write_text(
        """
        versions:
          v1:
            welcome: Hello.
        """
    )
    prompt_manager._load_all_prompts()
    with pytest.raises(ValueError, match="Version 'v9' not found for agent 'versioned'"):
        prompt_manager.get_prompt("versioned", "welcome", version="v9")


def test_get_prompt_versioned_missing_key(prompt_manager, tmp_path):
    """Test missing key error for versioned prompts."""
    test_file = tmp_path / "versioned.yaml"
    test_file.write_text(
        """
        versions:
          v1:
            welcome: Hello.
        """
    )
    prompt_manager._load_all_prompts()
    with pytest.raises(ValueError, match="Prompt not found: versioned.missing_key"):
        prompt_manager.get_prompt("versioned", "missing_key")


def test_get_available_versions(prompt_manager, tmp_path):
    """Test listing available versions for versioned and non-versioned agents."""
    flat = tmp_path / "flat.yaml"
    flat.write_text("description: Flat prompt.")
    versioned = tmp_path / "versioned.yaml"
    versioned.write_text(
        """
        default_version: stable
        versions:
          alpha:
            desc: Alpha
          beta:
            desc: Beta
          stable:
            desc: Stable
        """
    )
    prompt_manager._load_all_prompts()
    assert prompt_manager.get_available_versions("flat") == []
    assert prompt_manager.get_available_versions("versioned") == ["alpha", "beta", "stable"]


def test_versioned_agent_auto_select_first_version(prompt_manager, tmp_path):
    """Test auto-selecting first version when default_version is not specified."""
    test_file = tmp_path / "versioned.yaml"
    test_file.write_text(
        """
        versions:
          v1:
            welcome: |
              Hello (v1).
          v2:
            welcome: |
              Hello (v2).
        """
    )
    prompt_manager._load_all_prompts()
    result = prompt_manager.get_prompt("versioned", "welcome")
    assert result == "Hello (v1)."
