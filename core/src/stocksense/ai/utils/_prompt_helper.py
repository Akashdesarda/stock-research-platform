"""Utilities for fetching and formatting prompts from Phoenix server."""

from typing import Any, TypedDict

from phoenix.client import AsyncClient as PhoenixAsyncClient

from stocksense.config import get_settings

# Phoenix client singleton
settings = get_settings()
_phoenix_client: PhoenixAsyncClient | None = None


def get_phoenix_client() -> PhoenixAsyncClient:
    """Get or create the Phoenix client singleton.

    Returns
    -------
    PhoenixAsyncClient
        The singleton Phoenix async client instance.
    """
    global _phoenix_client
    if _phoenix_client is None:
        from phoenix.client import AsyncClient as PhoenixAsyncClient

        _phoenix_client = PhoenixAsyncClient(
            base_url=f"{settings.common.base_url}:{settings.common.phoenix_port}"
        )
    return _phoenix_client


class FormattedPrompt(TypedDict):
    """Structured prompt messages with role and content.

    Attributes
    ----------
    role : str
        The role of the message (e.g., 'system', 'user', 'assistant').
    content : str
        The content of the message.
    """

    role: str
    content: str


async def _fetch_prompt(
    prompt_identifier: str,
    variables: dict | None = None,
    **kwargs: Any,
) -> Any:
    """Internal function to fetch a prompt from Phoenix server.

    Parameters
    ----------
    prompt_identifier : str
        The identifier of the prompt to fetch.
    variables : dict, optional
        Variables to format the prompt with.
    **kwargs : Any
        Additional Phoenix-specific parameters (e.g., version, lang).

    Returns
    -------
    Any
        The formatted prompt object from Phoenix.
    """
    client = get_phoenix_client()
    prompt = await client.prompts.get(prompt_identifier=prompt_identifier, **kwargs)
    return prompt.format(variables=variables or {})


async def fetch_prompt_messages(
    prompt_identifier: str,
    variables: dict | None = None,
    **kwargs: Any,
) -> list[FormattedPrompt]:
    """Fetch and format a prompt from Phoenix server.

    Parameters
    ----------
    prompt_identifier : str
        The identifier of the prompt to fetch.
    variables : dict, optional
        Variables to format the prompt with.
    **kwargs : Any
        Phoenix parameters (version, lang, etc.) and prompt variables
        (e.g., table_name="users", version=2, lang="es").

    Returns
    -------
    list[FormattedPrompt]
        List of formatted prompt messages with 'role' and 'content' keys.

    Examples
    --------
    >>> msgs = await fetch_prompt_messages("text-to-sql", table_name="users")
    >>> msgs = await fetch_prompt_messages("text-to-sql", table_name="users", version=2, lang="es")
    """
    prompt = await _fetch_prompt(prompt_identifier, variables, **kwargs)
    messages = prompt.messages
    return [FormattedPrompt(role=m["role"], content=m["content"]) for m in messages]


async def fetch_system_prompt(
    prompt_identifier: str,
    variables: dict | None = None,
    **kwargs: Any,
) -> str:
    """Fetch system prompt by identifier.

    Parameters
    ----------
    prompt_identifier : str
        The identifier of the prompt to fetch.
    variables : dict, optional
        Variables to format the prompt with.
    **kwargs : Any
        Phoenix parameters (version, lang, etc.) and prompt variables.

    Returns
    -------
    str
        The content of the system prompt message.

    Raises
    ------
    ValueError
        If no system prompt is found in the retrieved prompt.

    Examples
    --------
    >>> system_prompt = await fetch_system_prompt("text-to-sql")
    >>> system_prompt = await fetch_system_prompt("text-to-sql", version=2, lang="es")
    """
    messages = await fetch_prompt_messages(prompt_identifier, variables, **kwargs)
    for msg in messages:
        if msg["role"] == "system":
            return msg["content"]
    raise ValueError(f"No system prompt found in prompt '{prompt_identifier}'.")


async def fetch_user_prompt(
    prompt_identifier: str,
    variables: dict | None = None,
    **kwargs: Any,
) -> str:
    """Fetch user prompt by identifier.

    Parameters
    ----------
    prompt_identifier : str
        The identifier of the prompt to fetch.
    variables : dict, optional
        Variables to format the prompt with.
    **kwargs : Any
        Phoenix parameters (version, lang, etc.) and prompt variables.

    Returns
    -------
    str
        The content of the user prompt message.

    Raises
    ------
    ValueError
        If no user prompt is found in the retrieved prompt.

    Examples
    --------
    >>> user_prompt = await fetch_user_prompt("text-to-sql", table_name="users")
    >>> user_prompt = await fetch_user_prompt("text-to-sql", version=2, table_name="users")
    """
    messages = await fetch_prompt_messages(prompt_identifier, variables, **kwargs)
    for msg in messages:
        if msg["role"] == "user":
            return msg["content"]
    raise ValueError(f"No user prompt found in prompt '{prompt_identifier}'.")


async def fetch_prompt_by_index(
    prompt_identifier: str,
    index: int,
    variables: dict | None = None,
    **kwargs: Any,
) -> str:
    """Fetch prompt message by index.

    Parameters
    ----------
    prompt_identifier : str
        The identifier of the prompt to fetch.
    index : int
        The zero-based index of the message to retrieve.
    variables : dict, optional
        Variables to format the prompt with.
    **kwargs : Any
        Phoenix parameters (version, lang, etc.) and prompt variables.

    Returns
    -------
    str
        The content of the message at the specified index.

    Raises
    ------
    ValueError
        If the index is out of range.

    Examples
    --------
    >>> system_prompt = await fetch_prompt_by_index("dataset-description", 0)
    >>> user_instruction = await fetch_prompt_by_index("dataset-description", 1, sql_query="SELECT *")
    """
    messages = await fetch_prompt_messages(prompt_identifier, variables, **kwargs)
    if index < 0 or index >= len(messages):
        raise ValueError(
            f"Prompt index {index} out of range. Prompt has {len(messages)} messages."
        )
    return messages[index]["content"]
