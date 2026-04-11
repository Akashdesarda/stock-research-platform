import os
from contextlib import contextmanager

import pystache
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models import Model, infer_model
from pydantic_ai.providers import infer_provider_class


@contextmanager
def temporary_env_var(key: str, value: str):
    """Temporarily sets an environment variable for the duration of the context."""
    original_value = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if original_value is None:
            del os.environ[key]
        else:
            os.environ[key] = original_value


def get_model(
    model_name: str, api_key: str, base_url: str | None = None
) -> Model:
    """
    Creates a model, explicitly passing connection settings for openai
    to avoid connection and environment variable issues.
    """
    if ":" not in model_name:
        # Fallback or default logic if needed
        raise ValueError(
            "No provider name given in model_name. E.G. --> groq:openai/gpt-oss-120b"
        )

    provider_name, actual_model_name = model_name.split(":", 1)
    # EG - google-gla -> google (since google have multiple providers). this is currently only
    # required for google ai studio models
    provider_prefix = provider_name.split("-")[0].upper()
    try:
        infer_provider_class(provider_name)
        # 2. Inject key, Infer Model, then Clean up
        env_var_name = f"{provider_prefix}_API_KEY"
        with temporary_env_var(env_var_name, api_key):
            # infer_model reads the env var we just set
            model = infer_model(model_name)

    except ValueError as e:
        # If the provider is unknown, but a base_url is provided, treat it as OpenAI-compatible
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        if base_url is None:
            raise ValueError(
                f"Provider '{provider_name}' must have base_url provided to treat it as OpenAI-compatible."
            ) from e

        provider = OpenAIProvider(api_key=api_key, base_url=base_url)
        model = OpenAIChatModel(actual_model_name, provider=provider)

    return model


def get_thinking_parts(messages: list[ModelMessage]) -> str:
    """Extracts the 'thinking' parts from the model's response."""
    thinking_content = []
    for message in messages:
        if isinstance(message, ModelResponse):
            thinking_content.extend(
                part.content
                for part in message.parts
                if isinstance(part, ThinkingPart)
            )

    return "\n".join(thinking_content)


def get_tool_call_parts(messages: list[ModelMessage]) -> list[dict]:
    """Extracts all tool calls and their corresponding returns from the message history."""
    tool_interactions = []

    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    tool_interactions.append(
                        {
                            "type": "call",
                            "tool_name": part.tool_name,
                            "tool_call_id": part.tool_call_id,
                            "args": part.args.args_dict
                            if hasattr(part.args, "args_dict")
                            else getattr(part.args, "args_json", part.args),
                        }
                    )

        elif isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    tool_interactions.append(
                        {
                            "type": "return",
                            "tool_name": part.tool_name,
                            "content": part.content,
                        }
                    )

    return tool_interactions


def render_mustache_conditional_prompt(template: str, data: dict):
    clean = {k: v for k, v in data.items() if v is not None}
    return pystache.render(template, clean)
