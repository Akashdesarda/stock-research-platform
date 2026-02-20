import logging

import reflex as rx
from httpx import AsyncClient
from stocksense.ai.agents import company_summary
from stocksense.ai.models import get_thinking_parts
from stocksense.config import get_settings

from webapp.state.shared import TickerSelectionMixin, ChatMixin, Message
from webapp.types import TickerChoice

logger = logging.getLogger("stocksense")
settings = get_settings()


class CompanySummaryState(TickerSelectionMixin, ChatMixin, rx.State):
    """State for the company summary research tool"""

    summary_result: str = ""

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

    @rx.event
    async def put_cache(self):
        """Putting the current AI prompt and generated summary into the cache."""
        # updating cache in stockdb as a event after generating the response.
        async with AsyncClient(timeout=None, follow_redirects=True) as client:
            response = await client.put(
                url=f"{settings.common.base_url}:{settings.stockdb.port}/api/operation/prompt/cache",
                json={
                    "agent": "company-summary",
                    "prompt": self.summary_prompt,
                    "model": settings.app.company_summary_model,
                    "response": self.summary_result,
                    "thinking": self.ai_thinking_part,
                    "ttl": 60 * 60 * 24,  # 1 day
                },
            )
            if response.status_code == 200:
                logger.info("Successfully updated prompt cache in StockDB.")
            else:
                logger.error(f"Failed to update prompt cache: {response.text}")

    @rx.event(background=True)
    async def get_summary(self):
        """Fetches the company summary based on the selected ticker."""
        async with self:
            if self.ai_is_generating:
                return
            self.ai_status_message = "Generating company summary..."
            self.ai_status_steps = ["Initializing request"]
            self.ai_is_generating = True

            # Add user prompt to chat window so they see what they asked
            # (Optional but good UX since they clicked a button instead of typing)
            self.messages.append(
                Message(role="user", content=self.summary_prompt)
            )

            use_cache = bool(self.ai_use_cache)

        model_name = settings.app.text_to_sql_model
        api_key = getattr(
            settings.common,
            f"{model_name.split(':')[0].split('-')[0].upper()}_API_KEY",
            "",
        )
        if not api_key:
            async with self:
                self.ai_error = "Missing API key for the text-to-SQL model."
                self.ai_status_message = ""
                self.ai_status_steps.append("Missing API key; cannot run model.")
                self.ai_is_generating = False
            return

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
                        self.ai_status_steps.append("Fetched summary from cache.")
                        self.ai_status_message = (
                            "Company summary generated successfully (from cache)."
                        )
                        # Append message when returning from cache
                        self.messages.append(
                            Message(role="assistant", content=self.summary_result)
                        )
                    return

            async with self:
                self.ai_status_steps.append(
                    "No cache entry found; generating via model."
                )

            cs_output = await company_summary(
                model_name=model_name,
                api_key=api_key,
                exchange=self.selected_exchange,
                ticker=self.selected_ticker[0],
            )
            async with self:
                self.ai_thinking_part = get_thinking_parts(cs_output.new_messages())
                self.ai_status_steps.append("Company summary fetched successfully.")
                self.summary_result = cs_output.output.text_output()

                # Append message directly to state while in `async with self`
                self.messages.append(
                    Message(role="assistant", content=self.summary_result)
                )

            # yield the cache update event after successful generation
            yield CompanySummaryState.put_cache

        except Exception as e:
            logger.error(f"Error fetching company summary: {e}")
            async with self:
                self.ai_error = f"Error fetching company summary: {str(e)}"
                self.ai_status_message = ""
                self.ai_status_steps.append(f"Summarization failed: {type(e).__name__}")
                raise e

        finally:
            async with self:
                self.ai_is_generating = False

    async def _try_fetch_cached_summary(self, prompt: str) -> tuple[str, str] | None:
        """Try to fetch cached company summary for a prompt"""
        try:
            async with AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.post(
                    url=f"{settings.common.base_url}:{settings.stockdb.port}"
                    f"/api/operation/prompt/search",
                    json={
                        "prompt": prompt,
                        "agent": "company-summary",
                        "cache_tier": "auto",
                    },
                )

            if response.status_code != 200:
                logger.warning(
                    f"Cannot fetch cached company summary due to HTTP status: {response.status_code}",
                )
                return None

            try:
                payload = response.json() or {}
            except Exception:
                logger.info("Cache lookup returned non-JSON; treating as miss.")
                return None

            cached_summary = payload.get("response") or ""
            cached_thinking = payload.get("thinking") or ""
            return cached_summary, cached_thinking

        except Exception:
            logger.info("Cache lookup failed; proceeding without cache.")
            return None
