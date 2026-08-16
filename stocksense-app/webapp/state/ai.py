import logging
import uuid

import polars as pl
import reflex as rx
from agno.os.schema import AgentSessionDetailSchema
from agno.run.agent import RunCompletedEvent, RunContentEvent

from webapp.state.shared import AgentRunMixin, ChatMixin, TickerSelectionMixin
from webapp.types import Message, RunState, TickerChoice

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
    chat_agent_id: str = "company-summary"
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

    async def _apply_loaded_session(self, detail: AgentSessionDetailSchema) -> None:
        """Restore ticker context and unlock chat_input after loading a session."""
        session_state = detail.session_state or {}
        exchange = session_state.get("exchange") or ""
        ticker = session_state.get("ticker") or ""

        async with self:
            messages = list(self.messages)

        first_assistant = next(
            (
                msg.content
                for msg in messages
                if msg.role == "assistant" and msg.content.strip()
            ),
            "",
        )

        exchange_dropdown = ""
        ticker_label = ""
        if exchange:
            exchanges = await self.available_exchanges
            match = exchanges.filter(pl.col("symbol") == exchange)
            if match.height > 0:
                exchange_dropdown = match.select("dropdown").item()
        if exchange and ticker:
            tickers = await self.available_tickers
            df = tickers.get(exchange)
            if df is not None and df.height > 0:
                match = df.filter(pl.col("ticker") == ticker)
                if match.height > 0:
                    ticker_label = match.select("dropdown").item()

        async with self:
            if exchange:
                self.selected_exchange = exchange
                if exchange_dropdown:
                    self.selected_exchange_dropdown = exchange_dropdown
            if ticker:
                self.selected_ticker = [ticker]
                self.selected_ticker_dropdown = ticker_label
                self.selected_ticker_dropdowns = [ticker_label] if ticker_label else []
            self.last_summary_exchange = exchange
            self.last_summary_ticker = ticker
            self.summary_result = first_assistant

    @rx.event(background=True)
    async def generate_summary(self):
        async with self:
            if (self.run_state == RunState.generating.value) or not self.selected_ticker:
                return
            exchange, ticker = self.selected_exchange, self.selected_ticker[0]
            prompt = (
                f"Generate company summary for {ticker} in the {exchange} exchange"
            )
            new_session = (exchange != self.last_summary_exchange) or (
                ticker != self.last_summary_ticker
            )

            if new_session:
                # Different company (or first run): mint a fresh Agno session and
                # reset the UI conversation. Dependencies populate session_state.
                self.current_session_id = str(uuid.uuid4())
                self.last_summary_exchange = exchange
                self.last_summary_ticker = ticker
                self.messages = []
                self.summary_result = ""
                self.run_state = RunState.idle.value
                self._session_titled = False

            # else: same company -> reuse current_session_id and keep messages.
            session_id = self._ensure_session_id()
            self.messages.append(Message(role="user", content=prompt))
            self.messages.append(Message(role="assistant", content=""))

        # manage_lifecycle=True: AgentRunMixin owns busy flag, status, steps, error handling, UI reset
        await self.stream_agent_run(
            agent_id="company-summary",
            message=prompt,
            session_id=session_id,
            dependencies=(
                {"exchange": exchange, "ticker": ticker} if new_session else {}
            ),
            on_content=self._on_content,
            on_complete=self._on_summary_completed,
            manage_lifecycle=True,
        )

    @rx.event(background=True)
    async def generate_answer(self):
        async with self:
            if (self.run_state == RunState.generating.value) or not self.current_session_id:
                return
            prompt = self.prompt.strip()
            if not prompt:
                return
            session_id = self.current_session_id
            # Do not set run_state=generating here — stream_agent_run(manage_lifecycle=True)
            # owns the busy window and will no-op if we mark generating first.
            self.messages.append(Message(role="user", content=prompt))
            self.prompt = ""  # rest the user prompt input field.
            self.messages.append(Message(role="assistant", content=""))

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
