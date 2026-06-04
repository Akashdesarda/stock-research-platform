from agno.models.base import Model


def get_model(
    model_name: str, api_key: str, base_url: str | None = None, **kwargs
) -> Model:
    """
    Creates an Agno model object based on the provider and model name.
    Expects model_name in the format 'provider:model_id'
    (e.g., 'groq:gpt-oss-120b').
    """
    if ":" not in model_name:
        raise ValueError(
            "No provider name given in model_name. E.G. --> groq:gpt-oss-120b"
        )

    provider, actual_model_id = model_name.split(":", 1)
    provider = provider.lower()

    from agno.models.anthropic import Claude
    from agno.models.google import Gemini
    from agno.models.groq import Groq
    from agno.models.openai import OpenAIChat, OpenAILike
    from agno.models.openrouter import OpenRouter

    provider_to_constructor = {
        "openai": OpenAIChat,
        "groq": Groq,
        "anthropic": Claude,
        "claude": Claude,
        "google": Gemini,
        "gemini": Gemini,
        "openrouter": OpenRouter,
    }

    constructor = provider_to_constructor.get(provider)
    if constructor is not None:
        return constructor(id=actual_model_id, api_key=api_key, **kwargs)

    # Fallback to OpenAI-compatible for unknown providers if base_url is present
    if base_url:
        return OpenAILike(
            id=actual_model_id, api_key=api_key, base_url=base_url, **kwargs
        )

    raise ValueError(
        f"Unsupported provider '{provider}'. "
        f"If it is OpenAI-compatible, please provide a base_url."
    )
