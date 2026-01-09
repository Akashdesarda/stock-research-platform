import hashlib
import json
import re
import unicodedata


def text_data_normalization(text: str) -> str:
    """
    Normalize prompt text safely for hashing.
    """

    # Normalize unicode (é vs é)
    text = unicodedata.normalize("NFKC", text)
    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Trim edges
    text = text.strip()

    # Collapse excessive spaces (but NOT newlines)
    text = re.sub(r"[ \t]+", " ", text)

    return text


def stable_hash(prompt: str, agent: str) -> str:
    """
    Create a forever-stable hash from structured input.
    """

    canonical = json.dumps(
        {
            "prompt": text_data_normalization(prompt),
            "agent": agent,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),  # Compact encoding without spaces
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
