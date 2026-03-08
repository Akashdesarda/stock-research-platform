from datetime import datetime, timedelta, timezone
from typing import List

from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_core import to_json


def history_messages_to_json(messages: list[ModelMessage]) -> str:
    """Converts the message history to a JSON string for storage or transmission"""
    return to_json(messages).decode("utf-8")


def json_to_history_messages(messages_json: str) -> list[ModelMessage]:
    """Converts a JSON string back into a list of ModelMessage objects"""
    return ModelMessagesTypeAdapter.validate_json(messages_json)


def condense_old_tool_calls(messages: List[ModelMessage]) -> List[ModelMessage]:
    """Strips tool execution data from old messages, keeping only the human/AI chat."""
    processed_messages = []

    # We keep the last 4 messages completely intact so the model still has
    # immediate context of what tools it just finished executing.
    keep_intact_threshold = len(messages) - 4

    for i, msg in enumerate(messages):
        if i >= keep_intact_threshold:
            processed_messages.append(msg)
            continue

        # For older messages, rebuild them keeping ONLY TextPart, UserPromptPart, and SystemPromptPart
        if isinstance(msg, ModelRequest):
            filtered_parts = [
                p
                for p in msg.parts
                if isinstance(p, (UserPromptPart, SystemPromptPart))
            ]
            if filtered_parts:
                processed_messages.append(
                    ModelRequest(parts=filtered_parts, timestamp=msg.timestamp)
                )

        elif isinstance(msg, ModelResponse):
            filtered_parts = [p for p in msg.parts if isinstance(p, TextPart)]
            if filtered_parts:
                processed_messages.append(
                    ModelResponse(parts=filtered_parts, timestamp=msg.timestamp)
                )
        else:
            # Pass through any other message types safely
            processed_messages.append(msg)

    return processed_messages


def loop_breaker_processor(messages: List[ModelMessage]) -> List[ModelMessage]:
    """Detects if the AI is repeating itself and injects a disruption prompt."""
    if len(messages) < 4:
        return messages

    # Get the last two AI responses
    ai_responses = [m for m in messages if isinstance(m, ModelResponse)]
    if len(ai_responses) >= 2:
        # Extract the text content from the last two responses
        last_resp = next(
            (
                p.content
                for p in ai_responses[-1].parts
                if isinstance(p, TextPart)
            ),
            None,
        )
        prev_resp = next(
            (
                p.content
                for p in ai_responses[-2].parts
                if isinstance(p, TextPart)
            ),
            None,
        )

        # If the model output the exact same text twice in a row
        if last_resp and last_resp == prev_resp:
            # Inject a silent user prompt to snap it out of the loop
            disruption = ModelRequest(
                parts=[
                    UserPromptPart(
                        content="[SYSTEM WARNING: You just repeated your exact previous response. You are stuck in a loop. Try a completely different approach or ask the user for clarification.]",
                    )
                ]
            )
            return messages + [disruption]

    return messages


def session_ttl_processor(messages: List[ModelMessage]) -> List[ModelMessage]:
    """Drops messages older than 2 hours to prevent stale context, while preserving system prompts."""
    if not messages:
        return messages

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
    cutoff_index = 0

    # We find the index of the first message that is NEWER than the cutoff time.
    # We do this instead of filtering out messages one-by-one to ensure we don't
    # inadvertently split up a matched pair of tool calls and tool returns.
    for i, msg in enumerate(messages):
        # We assume messages without timestamps are recent/current
        if hasattr(msg, "timestamp") and msg.timestamp:
            if msg.timestamp < cutoff_time:
                cutoff_index = i + 1
            else:
                break

    # If nothing is older than 2 hours, do nothing
    if cutoff_index == 0:
        return messages

    # We are about to drop messages[:cutoff_index]. We must rescue the SystemPromptPart!
    system_parts = []
    for msg in messages[:cutoff_index]:
        if isinstance(msg, ModelRequest):
            system_parts.extend(
                [p for p in msg.parts if isinstance(p, SystemPromptPart)]
            )

    recent_messages = messages[cutoff_index:]

    # If we rescued any system prompts, inject them back at the very beginning
    if system_parts:
        rescue_msg = ModelRequest(parts=system_parts)
        recent_messages.insert(0, rescue_msg)

    return recent_messages
