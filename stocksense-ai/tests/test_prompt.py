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
    invalid_file.write_text("invalid_yaml::: bad_format")

    prompt_manager._load_all_prompts()

    assert "invalid" in prompt_manager._prompt_registry
    assert prompt_manager._prompt_registry["invalid"] == {}
    assert "Error loading prompts" in caplog.text


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
