import logging
import uuid

import reflex as rx
from agno.run.agent import RunCompletedEvent, RunContentEvent

from webapp.state.shared import AgentRunMixin, ChatMixin, Message, TickerSelectionMixin
from webapp.types import RunState, TickerChoice

logger = logging.getLogger("stocksense")


# NOTE - ChatMixin must be first so _record_step attaches agent trace steps to the assistant message
# (inline_steps). TickerSelectionMixin brings in CommonMixin._record_step via inheritance; listing
# it before ChatMixin would shadow ChatMixin and break the per-message timeline
class CompanySummaryState(ChatMixin, TickerSelectionMixin, AgentRunMixin, rx.State):
    """State for the company summary research tool"""

    summary_result: str = ""
    run_state: str = RunState.idle.value
    # since the research work for single company, allowing only single ticker to be selected.
    allow_ticker_choice: bool = False
    ticker_choice: str = TickerChoice.desired.value
    desired_choice_as_multi_select: bool = False
    # Agno session used for the (summary + follow-up QA) conversation.
    current_session_id: str = ""
    # Last (exchange, ticker) the active session was created for — used to
    # decide whether a new Generate Summary click reuses the session.
    last_summary_exchange: str = ""
    last_summary_ticker: str = ""

    @rx.event
    def reset_chat(self):
        """Clear the summary conversation and allow a fresh Generate Summary run."""
        if self.run_state == RunState.generating.value:
            return
        # ChatMixin.reset_chat clears messages, session, prompt, and agent-run fields.
        super().reset_chat()
        # Page-specific bootstrap state so "New chat" unlocks Generate Summary again.
        self.summary_result = ""
        self.last_summary_exchange = ""
        self.last_summary_ticker = ""

    @rx.event(background=True)
    async def generate_summary(self):
        if (self.run_state == RunState.generating.value) or not self.selected_ticker:
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
                self.run_state = RunState.idle.value

            # else: same company -> reuse current_session_id and keep messages.
            self.messages.append(Message(role="user", content=prompt))
            self.messages.append(Message(role="assistant", content=""))

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

        # rename the session in the background
        async with self:
            await self.ai_client.rename_session(
                session_id=self.current_session_id,
                session_name=f"Company Summary: {ticker} on {exchange}",
            )

    @rx.event(background=True)
    async def generate_answer(self):
        if (self.run_state == RunState.generating.value) or not self.current_session_id:
            return

        prompt = self.prompt.strip()
        if not prompt:
            return

        async with self:
            # Do not set run_state=generating here — stream_agent_run(manage_lifecycle=True)
            # owns the busy window and will no-op if we mark generating first.
            self.messages.append(Message(role="user", content=prompt))
            self.prompt = ""  # rest the user prompt input field.
            self.messages.append(Message(role="assistant", content=""))
            session_id = self.current_session_id

        # Reuse the exact session generate_summary created earlier (no dependencies:
        # exchange/ticker already live in the agent's session_state).
        await self.stream_agent_run(
            agent_id="company-summary",
            message=prompt,
            session_id=session_id,
            on_content=self._on_content,
            on_complete=self._on_qa_completed,
            manage_lifecycle=True,
        )

    async def _on_content(self, event: RunContentEvent):
        """Append each text delta to the streaming assistant message."""
        async with self:
            # assigning inline steps to last assistant message
            self._update_last_assistant(append_content=event.content or "")

    async def _on_summary_completed(self, completed: RunCompletedEvent):
        async with self:
            # RunCompletedEvent.content is the full accumulated text; use it as the
            # authoritative final value for the streaming assistant message.
            final = completed.content or ""
            # assigning inline steps to last assistant message
            self._update_last_assistant(content=final)
            self.summary_result = final
            self.agent_status_message = "Company summary generated"

    async def _on_qa_completed(self, completed: RunCompletedEvent):
        async with self:
            # RunCompletedEvent.content is the full accumulated text; use it as the
            # authoritative final value for the streaming assistant message.
            self._update_last_assistant(content=completed.content or "")
            self.agent_status_message = ""
