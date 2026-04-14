import logging
import re
import uuid

import reflex as rx
from httpx import AsyncClient
from stocksense.ai.agents import (
    CompanySummaryOutput,
)
from stocksense.config import get_settings
from stocksense.types import AgentStructuredResponse

from webapp.state.shared import ChatMixin, Message, TickerSelectionMixin
from webapp.types import TickerChoice

logger = logging.getLogger("stocksense")
settings = get_settings()


class CompanySummaryState(TickerSelectionMixin, ChatMixin, rx.State):
    """State for the company summary research tool"""

    summary_result: str = ""
    qa_messages: list = []

    # Common variables needed for shared mixin
    allow_ticker_choice: bool = False
    ticker_choice: str = TickerChoice.desired.value
    desired_choice_as_multi_select: bool = False

    # Variables wrt AI response and status
    ai_is_generating: bool = False
    ai_status_message: str = ""
    ai_status_steps: list[str] = []
    ai_error: str = ""

    # Variables wrt to cache
    ai_use_cache: bool = True
    summary_prompt: str = ""
    ai_thinking_part: str = ""

    # Conversation session id
    current_session_id: str = ""

    def _client(self) -> AsyncClient:
        """Return a configured httpx AsyncClient."""
        return AsyncClient(
            timeout=None,
            follow_redirects=True,
            base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api",
        )

    @rx.event
    def set_summary_prompt(self):
        self.summary_prompt = f"Generate a company summary for {self.selected_ticker[0]} on {self.selected_exchange} exchange."

    @rx.event
    def set_ai_use_cache(self, value: bool):
        self.ai_use_cache = value
        if not value:
            self.ai_status_steps.append(
                "Cache disabled, will generate new summary on next generation."
            )
        else:
            self.ai_status_steps.append(
                "Cache enabled, will attempt to fetch from cache on next generation."
            )

    @rx.event(background=True)
    async def generate_summary(self):
        """Fetches the company summary based on the selected ticker."""
        async with self:
            if self.ai_is_generating:
                return
            self.ai_status_message = "Generating company summary..."
            self.ai_status_steps = ["Initializing request"]
            self.ai_is_generating = True
            self.ai_error = ""
            self.is_loading = False
            self.qa_messages = []
            # Add user prompt to chat window so they see what they asked
            # NOTE - resetting  messages from here onward since new company is selected.
            self.messages = [Message(role="user", content=self.summary_prompt)]
            self.current_session_id = str(uuid.uuid4())

            use_cache = bool(self.ai_use_cache)
        try:
            # Cache lookup (best-effort). Do not mutate the user's cache preference.
            if use_cache:
                async with self:
                    self.ai_status_steps.append("Checking prompt cache...")
                retrieved_cache = await self._try_fetch_cached_summary(
                    self.summary_prompt
                )
                if retrieved_cache is not None:
                    cached_summary, cached_thinking = retrieved_cache
                    async with self:
                        self.summary_result = cached_summary
                        self.ai_thinking_part = cached_thinking
                        self.ai_status_steps.append(
                            "Fetched summary from cache."
                        )
                        self.ai_status_message = "Company summary generated successfully (from cache)."
                        # Append message when returning from cache
                        self.messages.append(
                            Message(
                                role="assistant", content=self.summary_result
                            )
                        )
                    return

            async with self:
                self.ai_status_steps.append(
                    "No cache entry found; generating via model."
                )

            await self._generate_summary_via_llm()

        except Exception as e:
            logger.exception("Error generating company summary", exc_info=e)
            async with self:
                self.ai_error = (
                    f"Failed to generate company summary due to error: {str(e)}"
                )
                self.ai_status_message = ""
                self.ai_status_steps.append(
                    f"Summarization failed: {type(e).__name__}"
                )

        finally:
            async with self:
                self.ai_is_generating = False

    @rx.event(background=True)
    async def generate_answer(self):
        """Run QA for the current user prompt against the generated company summary."""
        async with self:
            if self.ai_is_generating:
                return

            prompt = self.prompt.strip()
            if not prompt:
                return

            self.ai_error = ""
            self.ai_status_message = "Generating answer..."
            self.ai_is_generating = True
            self.is_loading = True
            self.messages.append(Message(role="user", content=prompt))
            self.prompt = ""

        try:
            async with self:
                # Add an empty assistant message to stream into
                self.messages.append(Message(role="assistant", content=""))
                message_index = len(self.messages) - 1

            # Call the FastAPI streaming endpoint for QA
            async with self._client() as client:
                async with client.stream(
                    "POST",
                    "/agent/company-summary-qa",
                    json={
                        "model": settings.ai.company_summary_qa_model,
                        "prompt": prompt,
                        "ticker": self.selected_ticker[0],
                        "exchange": self.selected_exchange,
                        "session_id": self.current_session_id,
                    },
                ) as response:
                    response.raise_for_status()
                    # The backend streams the text deltas
                    full_text = ""
                    async for chunk in response.aiter_text():
                        if chunk:
                            full_text += chunk

                            # Decoding unicode escape sequences them back into their actual
                            # unicode characters so they render correctly in the UI.
                            content = re.sub(
                                r"\\u[0-9a-fA-F]{4}",
                                lambda m: chr(int(m.group(0)[2:], 16)),
                                full_text,
                            )
                            async with self:
                                # Update the message in place to trigger Reflex UI updates
                                self.messages[message_index] = Message(
                                    role="assistant", content=content
                                )
                            yield

            async with self:
                self.ai_status_message = ""

        except Exception as e:
            logger.error(f"Error during company summary QA: {e}")
            async with self:
                self.ai_error = f"Error during company summary QA: {str(e)}"
                self.ai_status_steps.append(f"QA failed: {type(e).__name__}")

        finally:
            async with self:
                self.ai_is_generating = False
                self.is_loading = False

    async def _try_fetch_cached_summary(
        self, prompt: str
    ) -> tuple[str, str] | None:
        """Try to fetch cached company summary for a prompt"""
        try:
            async with self._client() as client:
                response = await client.post(
                    url="/operation/prompt/search",
                    json={
                        "prompt": prompt,
                        "agent": "company-summary",
                        "cache_tier": "auto",
                    },
                )
            # Ensure non-2xx responses surface as HTTPStatusError
            response.raise_for_status()
            payload = response.json() or {}
            return payload.get("response", ""), payload.get("thinking", "")

        except Exception as e:
            logger.error(
                f"Cache lookup returned non-JSON due to {e}; treating as miss"
            )

    async def _generate_summary_via_llm(self):
        """Generate company summary via LLM without using cache."""
        async with self:
            self.ai_status_steps.append(
                f"Running model: {settings.ai.company_summary_model}."
            )
        # send the request
        try:
            async with self._client() as client:
                response = await client.post(
                    "/agent/company-summary",
                    json={
                        "model": settings.ai.company_summary_model,
                        "exchange": self.selected_exchange,
                        "ticker": self.selected_ticker[0],
                        "session_id": self.current_session_id,
                    },
                )
                # Ensure non-2xx responses surface as HTTPStatusError
                response.raise_for_status()
                result = AgentStructuredResponse.model_validate(response.json())
        except Exception as e:
            logger.error(f"Error during LLM generation: {e}")
            async with self:
                self.ai_error = f"Error during LLM generation: {e}"
                self.ai_status_message = ""
                return

        # updating UI state with LLM response
        async with self:
            self.summary_result = CompanySummaryOutput.model_validate(
                result.content
            ).text_output()
            self.ai_thinking_part = result.thinking or ""
            # TODO - add tool calls in steps
            self.ai_status_steps.append("Company summary fetched successfully.")
            self.ai_status_message = "Company summary generated successfully."
            # Append message directly to state while in `async with self`
            self.messages.append(
                Message(role="assistant", content=self.summary_result)
            )
