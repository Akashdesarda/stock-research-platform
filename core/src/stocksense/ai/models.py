import os
from contextlib import contextmanager

from pydantic_ai.models import Model, infer_model


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


def get_model(model_name: str, api_key: str) -> Model:
    """
    Creates a model using infer_model, injecting the API key automatically.
    Assumes standard naming convention: provider 'openai' -> env var 'OPENAI_API_KEY'.
    """
    # 1. Extract provider to guess the Env Var Name (e.g., 'openai' -> 'OPENAI_API_KEY')
    if ":" in model_name:
        provider_prefix = (
            model_name.split(":")[0]
            # EG google-gla -> google (since google have multiple providers)
            .split("-")[0]
            .upper()
        )
    else:
        # Fallback or default logic if needed
        raise ValueError(
            "No provider name given in model_name. E.G. --> groq:openai/gpt-oss-120b"
        )

    env_var_name = f"{provider_prefix}_API_KEY"

    # 2. Inject key, Infer Model, then Clean up
    with temporary_env_var(env_var_name, api_key):
        # infer_model reads the env var we just set
        model = infer_model(model_name)

    return model
