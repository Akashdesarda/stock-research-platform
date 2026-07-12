import logging
import uuid

import reflex as rx
from agno.run.agent import RunCompletedEvent, RunContentEvent

from webapp.state.shared import AgentRunMixin, ChatMixin, Message, TickerSelectionMixin
from webapp.types import TickerChoice

logger = logging.getLogger("stocksense")


class CompanySummaryState(TickerSelectionMixin, ChatMixin, AgentRunMixin, rx.State):
    """State for the company summary research tool"""

    summary_result: str = ""

    allow_ticker_choice: bool = False
    ticker_choice: str = TickerChoice.desired.value
    desired_choice_as_multi_select: bool = False

    # Agno session used for the (summary + follow-up QA) conversation.
    current_session_id: str = ""
    # Last (exchange, ticker) the active session was created for — used to
    # decide whether a new Generate Summary click reuses the session.
    last_summary_exchange: str = ""
    last_summary_ticker: str = ""

    # Index of the assistant message currently being streamed into (UI display).
    _stream_message_index: int = -1
    # Agno emits *delta* chunks via RunContentEvent.content so we accumulate deltas here and mirror
    # them onto the placeholder message.
    _stream_content: str = ""

    @rx.event(background=True)
    async def generate_summary(self):
        if self.agent_is_generating or not self.selected_ticker:
            return

        prompt = f"Generate company summary for {self.selected_ticker[0]} in the {self.selected_exchange} exchange"
        exchange, ticker = self.selected_exchange, self.selected_ticker[0]
        new_session = (exchange != self.last_summary_exchange) or (
            ticker != self.last_summary_ticker
        )

        async with self:
            if new_session:
                # Different company (or first run): mint a fresh Agno session and
                # reset the UI conversation. Dependencies populate session_state.
                self.current_session_id = str(uuid.uuid4())
                self.last_summary_exchange = exchange
                self.last_summary_ticker = ticker
                self.messages = []
                self.summary_result = ""

            # else: same company -> reuse current_session_id and keep messages.
            self._stream_content = ""
            self.messages.append(Message(role="user", content=prompt))
            self.messages.append(Message(role="assistant", content=""))
            self._stream_message_index = len(self.messages) - 1

        # manage_lifecycle=True: AgentRunMixin owns busy flag, status, steps, error handling, UI reset
        await self.stream_agent_run(
            agent_id="company-summary",
            message=prompt,
            session_id=self.current_session_id,
            dependencies=(
                {"exchange": exchange, "ticker": ticker} if new_session else {}
            ),
            on_content=self._on_content,
            on_complete=self._on_summary_completed,
            manage_lifecycle=True,
        )

    @rx.event(background=True)
    async def generate_answer(self):
        if self.agent_is_generating or not self.current_session_id:
            return

        prompt = self.prompt.strip()
        if not prompt:
            return

        async with self:
            self.is_loading = True
            self._stream_content = ""
            self.messages.append(Message(role="user", content=prompt))
            self.prompt = ""
            self.messages.append(Message(role="assistant", content=""))
            self._stream_message_index = len(self.messages) - 1

        # Reuse the exact session generate_summary created earlier (no dependencies:
        # exchange/ticker already live in the agent's session_state).
        await self.stream_agent_run(
            agent_id="company-summary",
            message=prompt,
            session_id=self.current_session_id,
            on_content=self._on_content,
            on_complete=self._on_qa_completed,
            manage_lifecycle=True,
        )

        # Always release the input button, even if the run errored.
        async with self:
            self.is_loading = False

    async def _on_content(self, event: RunContentEvent):
        """Append each text delta to the accumulator"""
        async with self:
            self._stream_content += event.content or ""
            if 0 <= self._stream_message_index < len(self.messages):
                self.messages[self._stream_message_index] = Message(
                    role="assistant", content=self._stream_content
                )

    async def _on_summary_completed(self, completed: RunCompletedEvent):
        async with self:
            # RunCompletedEvent.content is the full accumulated text. using it as authoritative final value
            self._stream_content = (
                completed.content
                if isinstance(completed.content, str)
                else str(completed.content or "")
            )
            self.summary_result = self._stream_content
            if 0 <= self._stream_message_index < len(self.messages):
                self.messages[self._stream_message_index] = Message(
                    role="assistant", content=self._stream_content
                )
            self.agent_steps.append("Summary generated successfully")
            self.agent_status_message = "Company summary generated"

    async def _on_qa_completed(self, completed):
        async with self:
            # Full accumulated text from the completed event.
            self._stream_content = (
                completed.content
                if isinstance(completed.content, str)
                else str(completed.content or "")
            )
            if 0 <= self._stream_message_index < len(self.messages):
                self.messages[self._stream_message_index] = Message(
                    role="assistant", content=self._stream_content
                )
            self.agent_status_message = ""
