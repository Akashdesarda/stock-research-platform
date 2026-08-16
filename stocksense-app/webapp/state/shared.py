import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Literal

import polars as pl
import reflex as rx
from agno.client.os import AgentOSClient, SessionType
from agno.os.schema import AgentSessionDetailSchema
from agno.run import RunStatus
from agno.run import agent as agent_event
from httpx2 import AsyncClient, HTTPStatusError, Timeout
from stocksense.config import get_settings

from webapp.types import ChatSessionItem, Message, RunState, TraceStep

logger = logging.getLogger("stocksense")
settings = get_settings()


def _format_session_timestamp(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _stringify_message_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        return text if isinstance(text, str) else str(text or "")
    if isinstance(content, list):
        return "".join(_stringify_message_content(part) for part in content)
    return str(content)


def _messages_from_chat_history(history: list) -> list[Message]:
    messages: list[Message] = []
    for item in history:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
        else:
            role = getattr(item, "role", None)
            content = getattr(item, "content", None)
        if hasattr(role, "value"):
            role = role.value
        if role not in ("user", "assistant"):
            continue
        text = _stringify_message_content(content).strip()
        if not text:
            continue
        messages.append(Message(role=role, content=text))
    return messages


def _run_sort_key(run) -> float:
    created = getattr(run, "created_at", None)
    if created is None:
        return 0
    if hasattr(created, "timestamp"):
        return created.timestamp()
    try:
        return float(created)
    except (TypeError, ValueError):
        return 0


def _messages_from_session_runs(runs: list) -> list[Message]:
    """Build user/assistant bubbles from AgentOS runs (one turn per run)."""
    messages: list[Message] = []
    for run in sorted(runs, key=_run_sort_key):
        user_text = _stringify_message_content(getattr(run, "run_input", None)).strip()
        if user_text:
            messages.append(Message(role="user", content=user_text))
        assistant_text = _stringify_message_content(getattr(run, "content", None)).strip()
        if assistant_text:
            messages.append(Message(role="assistant", content=assistant_text))
    return messages


class CommonMixin(rx.State, mixin=True):
    """A mixin state for common StockDB data."""

    selected_exchange: str = ""
    selected_ticker: list[str] = []
    trace_steps: list[TraceStep] = []
    steps_open: bool = False

    @rx.var
    async def available_exchanges(self) -> pl.DataFrame:
        """Get the available stock exchanges from StockDB.

        Returns:
            A DataFrame of available stock exchanges.
        """
        async with self._stockdb_client() as client:
            response = await client.get("/per-security")
            response.raise_for_status()
            # NOTE - response --> [exchange_symbol: exchange_name]
            exch_response = response.json()
            # NOTE - df --> | exch_symbol | exch_name | exch_name (exch_symbol) |
            return pl.DataFrame({
                "symbol": exch_response.keys(),
                "name": exch_response.values(),
            }).with_columns(dropdown=pl.col("name") + " (" + pl.col("symbol") + ")")

    @rx.var
    async def exchange_dropdown_list(self) -> list[str]:
        """Get the list of available exchanges for the dropdown."""
        df = await self.available_exchanges
        return df.select("dropdown").to_series().to_list()

    @rx.var
    async def available_tickers(self) -> dict[str, pl.DataFrame]:
        """Get the available tickers for each exchange"""
        async with self._stockdb_client() as client:
            response = await client.get("/bulk/list-tickers")
            # NOTE - response --> {exchange_symbol: [{ticker, company},...]}
            tickers_wrt_exchange = response.json()
            available_tickers = dict.fromkeys(
                tickers_wrt_exchange.keys(), pl.DataFrame()
            )

            for exch in available_tickers:
                if not tickers_wrt_exchange[exch]:
                    available_tickers[exch] = pl.DataFrame({
                        "ticker": [],
                        "company": [],
                    }).with_columns(dropdown=pl.lit(""))
                else:
                    available_tickers[exch] = pl.DataFrame(tickers_wrt_exchange[exch])
                    available_tickers[exch] = available_tickers[exch].with_columns(
                        dropdown=pl.col("ticker") + " - " + pl.col("company")
                    )
            # NOTE - available_tickers --> {exchange_symbol: df(ticker, company, ticker - company)}
            return available_tickers

    @rx.var
    async def ticker_dropdown_list(self) -> list[str]:
        """Get the list of available tickers for the selected exchange."""
        _ = await self.available_tickers
        if not self.selected_exchange or self.selected_exchange not in _:
            return []
        df = _[self.selected_exchange]
        return df.select("dropdown").to_series().to_list()

    @rx.var
    async def ticker_history_columns(self) -> list[str]:
        """Fetch column names for the stock history table."""
        async with self._stockdb_client() as client:
            response = await client.get(
                url="/per-security/nse/tcs/history",
                params={"interval": "1d", "period": "1d"},
            )
            if response.status_code != 200:
                return []
            payload = response.json()
            return list(payload[0].keys()) if payload else []

    @rx.event
    async def get_exchange_symbol(self, dropdown_value: str):
        """Extract the exchange symbol from the dropdown value.

        Args:
            dropdown_value: The selected dropdown value.
        Returns:
            The exchange symbol.
        """
        _ = await self.available_exchanges
        self.selected_exchange = (
            _.filter(pl.col("dropdown") == dropdown_value).select("symbol").item()
        )

    @rx.event
    async def get_ticker_symbols(self, dropdown_values: list[str]):
        """Extract the ticker symbols from the dropdown values.

        Args:
            dropdown_values: The selected dropdown values.
        Returns:
            The list of ticker symbols.
        """
        _ = await self.available_tickers
        df = _[self.selected_exchange]
        self.selected_ticker = (
            df
            .filter(pl.col("dropdown").is_in(dropdown_values))
            .select("ticker")
            .to_series()
            .to_list()
        )

    @rx.event
    async def toggle_steps(self):
        """Toggle the collapse state of the ticker selection form."""
        self.steps_open = not self.steps_open

    def _record_step(self, step: TraceStep):
        """Append to the flat trace log used by workflow_steps.

        CommonMixin, ChatMixin, and AgentRunMixin each define _record_step.
        Python MRO picks the first matching implementation in the state class
        bases. Chat states must list ChatMixin before TickerSelectionMixin
        (which inherits CommonMixin) so steps also attach to msg.steps for
        inline_steps — otherwise only trace_steps is updated and the chat
        timeline stays empty.
        """
        self.trace_steps = [*self.trace_steps, step]

    def _reset_steps(self):
        self.trace_steps = []
        self.steps_open = True

    def _stockdb_client(self) -> AsyncClient:
        """Return a configured httpx AsyncClient."""
        return AsyncClient(
            timeout=Timeout(connect=5, read=120, write=120, pool=10),
            follow_redirects=True,
            base_url=f"{settings.common.base_url}:{settings.stockdb.port}/api",
        )


class TickerSelectionMixin(CommonMixin, mixin=True):
    """Mixin for interactive ticker selection state logic."""

    # Form fields
    selected_exchange_dropdown: str = ""
    allow_ticker_choice: bool = True
    ticker_choice: str = "Index Based"
    selected_ticker_dropdown: str = ""
    selected_ticker_dropdowns: list[str] = []
    index_choice: str = ""
    desired_choice_as_multi_select: bool = True

    @rx.var
    async def exchange_wise_index(self) -> dict:
        async with self._stockdb_client() as client:
            response = await client.get("/bulk/list-indexes")
            return response.json()

    @rx.var
    async def available_index(self) -> list[str]:
        _ = await self.exchange_wise_index
        # NOTE: self.selected_exchange comes from CommonMixin
        return _.get(self.selected_exchange, [])

    @rx.event
    async def set_exchange_dropdown(self, value: str):
        self.selected_exchange_dropdown = value
        self.selected_ticker_dropdown = ""
        self.selected_ticker_dropdowns = []
        self.selected_ticker = []
        self.index_choice = ""
        # NOTE: get_exchange_symbol comes from CommonMixin
        await self.get_exchange_symbol(value)

    @rx.event
    async def set_ticker_choice(self, value: str):
        self.ticker_choice = value

        # NOTE - for "All" committing right away
        if value == "All":
            # NOTE: available_tickers comes from CommonMixin
            _ = await self.available_tickers
            df = _[self.selected_exchange]
            self.selected_ticker = df.select("ticker").to_series().to_list()
        else:
            self.selected_ticker = []

    @rx.event
    async def set_index_choice(self, value: str):
        self.index_choice = value
        await self.get_tickers_for_index()

    @rx.event
    async def get_tickers_for_index(self):
        async with self._stockdb_client() as client:
            # NOTE - response --> [{ticker, company},...]
            response = await client.get(
                f"/per-security/{self.selected_exchange}/{self.index_choice}"
            )
        self.selected_ticker = [i["ticker"] for i in response.json()]

    @rx.event
    async def get_tickers_for_desired(self, values: list[str] | str):
        if isinstance(values, str):
            normalized_values = [values] if values else []
            self.selected_ticker_dropdown = values
        else:
            normalized_values = values
            self.selected_ticker_dropdown = values[0] if values else ""

        self.selected_ticker_dropdowns = normalized_values
        # NOTE: get_ticker_symbols comes from CommonMixin
        await self.get_ticker_symbols(normalized_values)


class ChatMixin(rx.State, mixin=True):
    """A mixin state for common chat data."""

    prompt: str = ""
    messages: list[Message] = []
    run_state: str = RunState.idle.value
    trace_steps: list[TraceStep] = []
    # Optional Agno session id used by multi-turn chat pages.
    current_session_id: str = ""
    # AgentOS component_id used to list/load sessions for this chat page.
    chat_agent_id: str = ""
    sessions_open: bool = False
    session_list: list[ChatSessionItem] = []
    sessions_loading: bool = False
    sessions_error: str = ""
    _session_titled: bool = False

    @rx.event
    def set_prompt(self, value: str):
        self.prompt = value

    @rx.event
    def reset_prompt(self):
        self.prompt = ""
        # self.is_loading = True

    @rx.event
    def reset_chat(self):
        """Clear the conversation so the next message starts a fresh session."""
        if self.run_state == RunState.generating.value:
            return
        self.current_session_id = ""
        self.messages = []
        self.prompt = ""
        self.run_state = RunState.idle.value
        self._session_titled = False
        self._reset_steps()
        # AgentRunMixin fields (present when this mixin is composed with it).
        self.agent_error = ""
        self.agent_status_message = ""
        self.agent_run_id = ""
        self._active_agent_id = ""

    @rx.event
    def set_sessions_open(self, is_open: bool):
        """Open or close the session history drawer; refresh the list on open."""
        self.sessions_open = is_open
        if is_open:
            return type(self).load_sessions

    @rx.event(background=True)
    async def load_sessions(self):
        """Fetch recent AgentOS sessions for this chat page's agent."""
        async with self:
            agent_id = self.chat_agent_id
            if not agent_id:
                self.sessions_loading = False
                self.sessions_error = "No agent configured for this chat."
                return
            self.sessions_loading = True
            self.sessions_error = ""

        try:
            client = self._ai_client()
            result = await client.get_sessions(
                session_type=SessionType.AGENT,
                component_id=agent_id,
                sort_by="updated_at",
                sort_order="desc",
                limit=20,
            )
            items = [
                ChatSessionItem(
                    session_id=sess.session_id,
                    session_name=sess.session_name or sess.session_id[:8],
                    updated_at=_format_session_timestamp(sess.updated_at),
                )
                for sess in result.data
            ]
            async with self:
                self.session_list = items
                self.sessions_loading = False
        except Exception as e:
            logger.exception("Failed to load chat sessions", extra={"error": str(e)})
            async with self:
                self.session_list = []
                self.sessions_loading = False
                self.sessions_error = "Failed to load sessions."

    @rx.event(background=True)
    async def select_session(self, session_id: str):
        """Restore a past session into the chat window and continue it."""
        async with self:
            if self.run_state == RunState.generating.value or not session_id:
                return

        try:
            client = self._ai_client()
            detail = await client.get_session(
                session_id, session_type=SessionType.AGENT
            )
            loaded_id = getattr(detail, "session_id", None) or session_id
            runs = await client.get_session_runs(
                loaded_id, session_type=SessionType.AGENT
            )
            messages = _messages_from_session_runs(runs)
            if not messages:
                messages = _messages_from_chat_history(
                    getattr(detail, "chat_history", None) or []
                )
            async with self:
                self.current_session_id = loaded_id
                self.messages = messages
                self.prompt = ""
                self.run_state = RunState.idle.value
                self._session_titled = True
                self.sessions_open = False
                self.sessions_error = ""
                self._reset_steps()
                self.agent_error = ""
                self.agent_status_message = ""
                self.agent_run_id = ""
            await self._apply_loaded_session(detail)
        except Exception as e:
            logger.exception(
                "Failed to load chat session", extra={"error": str(e)}
            )
            async with self:
                self.sessions_error = "Failed to load session."

    def _ensure_session_id(self) -> str:
        """Return the active Agno session id, minting one only for a new chat.

        Must be called inside `async with self` in background events.
        Once set (new chat or loaded past session), the same id is reused for
        every subsequent run in this thread. AgentOS treats session_id="" as
        missing and starts a new session.
        """
        if not self.current_session_id:
            self.current_session_id = str(uuid.uuid4())
            self._session_titled = False
        return self.current_session_id

    async def _apply_loaded_session(self, detail: AgentSessionDetailSchema) -> None:
        """Hook for page-specific restore after a session is loaded."""
        return

    async def _after_run_completed(self) -> None:
        """Auto-title the conversation after the first successful run."""
        await self._maybe_auto_title_session()

    async def _maybe_auto_title_session(self) -> None:
        """Name a new session via AgentOS session-title + rename_session."""
        async with self:
            if self._session_titled or not self.current_session_id:
                return
            session_id = self.current_session_id
            first_user = next(
                (
                    msg.content
                    for msg in self.messages
                    if msg.role == "user" and msg.content.strip()
                ),
                "",
            )
            if not first_user:
                return
            # Claim the title slot so concurrent completions don't double-rename.
            self._session_titled = True

        try:
            client = self._ai_client()
            response = await client.run_agent(
                agent_id="session-title",
                message=(
                    "Generate a title for the session based on the following "
                    f"user prompt: {first_user}"
                ),
            )
            if response.status != RunStatus.completed:
                raise RuntimeError(
                    f"session-title run did not complete (status={response.status})"
                )

            content = response.content
            if isinstance(content, dict):
                title = content.get("title")
            else:
                title = getattr(content, "title", None)
            if not title or not str(title).strip():
                raise RuntimeError("session-title returned no title")

            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    await client.rename_session(
                        session_id=session_id,
                        session_name=str(title).strip(),
                        session_type=SessionType.AGENT,
                    )
                    last_error = None
                    break
                except HTTPStatusError as e:
                    last_error = e
                    status = e.response.status_code if e.response is not None else None
                    if status == 404 and attempt < 2:
                        # Session upsert may still be flushing; retry briefly.
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    raise
            if last_error is not None:
                raise last_error
        except Exception as e:
            logger.exception(
                "Failed to auto-title chat session (session may not be persisted)",
                extra={"error": str(e), "session_id": session_id},
            )
            async with self:
                self._session_titled = False

    @rx.event
    async def append_message(self, role: Literal["user", "assistant"], content: str):
        if not content.strip():
            return

        self.messages.append(Message(role=role, content=content))

        # Reset the prompt only if the message is from the user
        if role == "user":
            yield type(self).reset_prompt

    @rx.event
    def toggle_message_steps(self, index: int):
        msg = self.messages[index]
        self.messages[index] = Message(
            role=msg.role,
            content=msg.content,
            steps=msg.steps,
            steps_open=not msg.steps_open,
        )

    def _record_step(self, step: TraceStep):
        """Record a trace step for chat UIs (inline_steps + workflow_steps).

        Writes to trace_steps and, when the last message is an assistant
        bubble, appends the same step to msg.steps. This method must win MRO
        over CommonMixin (via TickerSelectionMixin) and AgentRunMixin on chat
        state classes — put ChatMixin first in their base list.
        """
        self.trace_steps = [*self.trace_steps, step]
        if self.messages and self.messages[-1].role == "assistant":
            last = self.messages[-1]
            self.messages[-1] = Message(
                role="assistant",
                content=last.content,
                steps=[*last.steps, step],
                steps_open=True if not last.steps else last.steps_open,
                run_state=last.run_state,
            )

    def _reset_steps(self):
        self.trace_steps = []

    def _update_last_assistant(
        self,
        *,
        content: str | None = None,
        append_content: str | None = None,
    ):
        """Update the streaming assistant message while preserving steps."""
        if not (self.messages and self.messages[-1].role == "assistant"):
            return
        last = self.messages[-1]
        new_content = last.content
        # appending text delta for streaming assistant
        if append_content is not None:
            new_content = last.content + append_content
        # replacing the entire message content for non-streaming assistant
        if content is not None:
            new_content = content
        self.messages[-1] = Message(
            role="assistant",
            content=new_content,
            # preserve steps and state
            steps=last.steps,
            steps_open=last.steps_open,
            run_state=last.run_state,
        )


class AgentRunMixin(rx.State, mixin=True):
    """A mixin state for common agent run data."""

    run_state: str = RunState.idle.value
    trace_steps: list[TraceStep] = []
    messages: list[Message] = []

    agent_run_id: str = ""
    agent_error: str = ""
    agent_status_message: str = ""

    _active_agent_id: str = ""

    @rx.var
    def has_resumable_run(self) -> bool:
        """True when the last run was cancelled/errored and could be resumed (future)."""
        return self.run_state in (RunState.cancelled.value, RunState.error.value)

    async def agent_run(self, **kwargs) -> agent_event.RunOutput:
        async with self:
            self._active_agent_id = kwargs["agent_id"]
            self._record_step(
                TraceStep(name=f"Running agent {kwargs['agent_id']}", icon="bot")
            )
        try:
            client = self._ai_client()
            run_output = await client.run_agent(**kwargs)
            async with self:
                self.agent_run_id = run_output.run_id
                self._record_step(
                    TraceStep(
                        name=f"Agent {kwargs['agent_id']} completed run", icon="bot"
                    )
                )
            return run_output

        except Exception as e:
            logger.exception("Agent stream failed", exc_info=e)
            async with self:
                self._record_step(
                    TraceStep(
                        name=f"Agent {kwargs['agent_id']} failed to generate",
                        icon="bot",
                        detail=str(e),
                        passed=False,
                    )
                )
                self.agent_error = f"Failed to generate due to error: {e}."
            # Re-raise to preserve return type contract
            raise

    async def stream_agent_run(
        self,
        on_content: Callable[[agent_event.RunContentEvent], Awaitable[None]]
        | None = None,
        on_complete: Callable[[agent_event.RunCompletedEvent], Awaitable[None]]
        | None = None,
        manage_lifecycle: bool = True,
        **kwargs,
    ):
        async with self:
            # Record the active agent id up front (always, regardless of lifecycle mode) so
            # cancel_agent_run can target the right run even when manage_lifecycle=False.
            self._record_step(
                TraceStep(name=f"Running agent {kwargs['agent_id']}", icon="bot")
            )
            self._active_agent_id = kwargs["agent_id"]

            # manage_lifecycle=True: the mixin owns the generating state window (sets/resets + guards).
            # manage_lifecycle=False: the caller owns it (e.g. to wrap pre-stream work like cache lookup).
        if manage_lifecycle:
            # Guard: a run is already in flight, ignore the new request (prevents overlapping runs).
            if self.run_state == RunState.generating.value:
                return

            # Update UI state before starting the agent run
            async with self:
                # Mark busy: flips button to disabled + shows spinner in the UI.
                self.run_state = RunState.generating.value
                self.agent_error = ""
                self.agent_status_message = "Generating…"
                self.agent_run_id = ""
                self._reset_steps()
                self._set_last_assistant_run_state(RunState.generating)

        try:
            client = self._ai_client()
            completed = None

            async for event in client.run_agent_stream(**kwargs):
                if isinstance(event, agent_event.RunStartedEvent):
                    async with self:
                        self.agent_run_id = event.run_id
                        # In background events `self` is a StateProxy — use hasattr,
                        # not type(self).get_fields().
                        if event.session_id and hasattr(self, "current_session_id"):
                            current = self.current_session_id
                            if not current:
                                # First turn with no client-minted id: adopt server id.
                                self.current_session_id = event.session_id
                            elif current != event.session_id:
                                # Keep the intentional thread id (new chat or loaded past).
                                logger.warning(
                                    "Ignoring AgentOS session_id=%s; keeping "
                                    "intentional session_id=%s for agent=%s",
                                    event.session_id,
                                    current,
                                    event.agent_id,
                                )
                        self._record_step(
                            TraceStep(
                                name="Running model",
                                icon="brain",
                                detail=f"Model: {event.model}",
                            )
                        )
                        logger.debug(
                            f"using model {event.model} for agent: {event.agent_id} with run_id: {self.agent_run_id}"
                        )
                # Tool calling events - guard against None tool
                elif isinstance(event, agent_event.ToolCallStartedEvent):
                    if event.tool and event.tool.tool_name:
                        async with self:
                            self._record_step(
                                TraceStep(
                                    name="Tool calling",
                                    icon="hammer",
                                    detail=f"Tool: {event.tool.tool_name}",
                                )
                            )
                elif isinstance(event, agent_event.ToolCallCompletedEvent):
                    if event.tool and event.tool.tool_name:
                        async with self:
                            self._record_step(
                                TraceStep(
                                    name="Tool completed",
                                    icon="circle_check_big",
                                    detail=f"Tool: {event.tool.tool_name}",
                                )
                            )
                elif isinstance(event, agent_event.ToolCallErrorEvent):
                    if event.tool and event.tool.tool_name:
                        async with self:
                            self._record_step(
                                TraceStep(
                                    name="Tool error",
                                    icon="circle_x",
                                    detail=f"Tool: {event.tool.tool_name}",
                                    passed=False,
                                )
                            )
                # Content delta event
                elif isinstance(event, agent_event.RunContentEvent):
                    if on_content:
                        await on_content(event)
                # Cancellation event
                elif isinstance(event, agent_event.RunCancelledEvent):
                    async with self:
                        self._record_step(
                            TraceStep(
                                name="Request cancelled",
                                icon="circle_minus",
                                passed=False,
                            )
                        )
                        self.agent_status_message = "Request cancelled"
                        # Mark both the global and per-message state as resumable.
                        self.run_state = RunState.cancelled.value
                        self._set_last_assistant_run_state(RunState.cancelled)
                    return
                # Error event
                elif isinstance(event, agent_event.RunErrorEvent):
                    async with self:
                        self._record_step(
                            TraceStep(
                                name=f"Agent {kwargs['agent_id']} failed to generate",
                                icon="bot",
                                detail=f"Error: {event.content}",
                                passed=False,
                            )
                        )
                        self.agent_status_message = (
                            "Generation failed. Please try again later."
                        )
                        self.agent_error = event.content
                        self.run_state = RunState.error.value
                        self._set_last_assistant_run_state(RunState.error)
                        logger.error(f"Run error: {event.content}")
                    return
                # Completion event
                elif isinstance(event, agent_event.RunCompletedEvent):
                    completed = event
                    logger.debug(f"{completed.run_id} agent run completed successfully")

            # processing the completion event
            if completed is None:
                async with self:
                    self.agent_error = "Generation ended without a completion event"
                    self.agent_status_message = "Generation failed"
                    self.run_state = RunState.error.value
                    self._set_last_assistant_run_state(RunState.error)
                return
            if on_complete:
                await on_complete(completed)

            # Clean finish with LLM output
            async with self:
                self._record_step(
                    TraceStep(
                        name=f"Agent {kwargs['agent_id']} completed run", icon="bot"
                    )
                )
                self.run_state = RunState.completed.value
                self._set_last_assistant_run_state(RunState.completed)

            await self._after_run_completed()

        except Exception as e:
            logger.exception("Agent stream failed", exc_info=e)
            async with self:
                self._record_step(
                    TraceStep(
                        name=f"Agent {kwargs['agent_id']} failed to generate",
                        icon="bot",
                        detail=f"Error: {e}",
                        passed=False,
                    )
                )
                self.agent_error = f"Failed to generate due to error: {e}."
                self.agent_status_message = ""
                self.run_state = RunState.error.value
                self._set_last_assistant_run_state(RunState.error)

        finally:
            if manage_lifecycle:
                async with self:
                    # Only reset to idle if we ended in a terminal *non-resumable*
                    # state. Preserve cancelled/error so resume UI stays available.
                    if self.run_state == RunState.generating.value:
                        # Safety net: stream ended without a terminal event.
                        self.run_state = RunState.completed.value
                        self._set_last_assistant_run_state(RunState.completed)

    @rx.event
    async def cancel_agent_run(self):
        """Request server-side cancellation of the active run."""
        if self.run_state != RunState.generating.value or not self.agent_run_id:
            return
        try:
            client = self._ai_client()
            self._record_step(
                TraceStep(name="Canceling agent run", icon="circle_minus", passed=False)
            )
            await client.cancel_agent_run(
                agent_id=self._active_agent_id,
                run_id=self.agent_run_id,
            )
        except Exception as e:
            logger.error("Cancel request failed", exc_info=e)
            async with self:
                self.agent_error = f"Failed to cancel run: {e}"

    @rx.event(background=True)
    async def resume_agent_run(self, message_index: int):
        """Resume a previously cancelled/interrupted run"""
        if not self.has_resumable_run:
            return
        # TODO - Agno's resume api
        raise NotImplementedError("Resume not yet implemented — pending Agno API.")

    async def _after_run_completed(self) -> None:
        """Hook after a successful streamed run. ChatMixin auto-titles sessions."""
        return

    def _ai_client(self) -> AgentOSClient:
        return AgentOSClient(f"{settings.ai.ai_url}:{settings.ai.port}")

    def _set_last_assistant_run_state(self, state: RunState):
        """Stamp the run_state onto the streaming assistant message."""
        if self.messages and self.messages[-1].role == "assistant":
            last = self.messages[-1]
            self.messages[-1] = Message(
                role="assistant",
                content=last.content,
                steps=last.steps,
                steps_open=last.steps_open,
                run_state=state.value,
            )

    def _record_step(self, step: TraceStep):
        """Append to trace_steps only (workflow_steps on non-chat pages).

        On states that also use ChatMixin, this implementation is shadowed
        unless ChatMixin is listed earlier in the class bases. Non-chat states
        (e.g. DataState) should not include ChatMixin; AgentRunMixin order
        relative to TickerSelectionMixin only affects which flat-log variant runs.
        """
        self.trace_steps = [*self.trace_steps, step]

    def _reset_steps(self):
        """Clear the flat step log."""
        self.trace_steps = []
