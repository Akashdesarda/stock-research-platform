import os

import polars as pl
import streamlit as st
from stocksense.ai.agents import company_summary, company_summary_qa
from stocksense.config import get_settings

from app.core.utils import (
    get_available_exchanges,
    get_available_tickers,
)
from app.pages.ai._helper import render_chat, stream_text
from app.state.manager import StateManager
from app.state.model import (
    ChatMessage,
    PageKey,
    ResearchPageAppSate,
    ResearchPageAvailableTools,
    ResearchPhase,
)

settings = get_settings(os.getenv("CONFIG_FILE"))
state = StateManager.init(PageKey.data.value, ResearchPageAppSate)
available_exchange = get_available_exchanges()
available_tickers = get_available_tickers()


def company_summary_callback(exchange, ticker):
    state.company_summary = company_summary(
        model_name=settings.app.company_summary_model,
        api_key=getattr(
            settings.common,
            f"{settings.app.company_summary_model.split(':')[0].split('-')[0].upper()}_API_KEY",
        ),
        exchange=exchange,
        ticker=ticker,
    )


welcome = (
    "Hello there! I am Stocksense AI here to help you research about any listed company. To "
    "get started first select Exchange & Ticker (Company) that you want to research"
)


st.title("🔍 Market Research & Analysis")
st.markdown("Comprehensive research tools for informed investment decisions.")

# SECTION - Sidebar dropdown to choose research tool
with st.sidebar:
    selected_tool = st.selectbox(
        "Select tools to research",
        options=list(ResearchPageAvailableTools),
        format_func=lambda x: x.value,
    )

# SECTION - Company Summary
if selected_tool is ResearchPageAvailableTools.company_summary:
    if not state.messages:
        with st.chat_message("assistant", avatar=None):
            st.write("Company Summary Agent")
            streamed_welcome = st.write_stream(stream_text(welcome))
        state.messages.append(ChatMessage(role="assistant", content=welcome))
        st.rerun()

    render_chat(state.messages)  # NOTE - always render chat from state

    # SECTION - Exchange + Ticker selection (INIT phase only)
    if state.phase is ResearchPhase.INIT:
        exchange_col, ticker_col = st.columns(2)
        # exchange selection dropdown
        with exchange_col:
            if exchange_label := st.selectbox(
                "Select Exchange",
                options=available_exchange.select("dropdown").to_series().to_list(),
                index=None,  # No defaults
            ):
                # get actual value & assign to state
                exchange = (
                    available_exchange.filter(pl.col("dropdown") == exchange_label)
                    .select("symbol")
                    .item()
                )
        # ticker selection dropdown
        with ticker_col:
            # ticker_label = None
            if exchange_label:
                if ticker_label := st.selectbox(
                    "Select listed Company",
                    options=available_tickers[exchange]["dropdown"].to_list(),
                    index=None,  # No defaults
                ):
                    ticker = (
                        available_tickers[exchange]
                        .filter(pl.col("dropdown") == ticker_label)
                        .select("ticker")
                        .item()
                    )

        if submit := st.button(
            "Submit", icon=":material/play_arrow:", type="secondary"
        ):
            if not exchange or not ticker:
                st.warning("Please select both exchange and company")
                st.stop()

            state.selected_exchange = exchange
            state.selected_ticker = ticker

            state.messages.append(
                ChatMessage(
                    role="user",
                    content=f"Analyze {state.selected_ticker} listed on {state.selected_exchange}",
                )
            )
            st.rerun()

    # SECTION - Company Summary
    if (
        state.phase is ResearchPhase.INIT
        and state.selected_exchange
        and state.selected_ticker
    ):
        with st.chat_message("assistant"):
            st.write(
                "Gathering & analyzing information about the company you have selected"
            )
            cs_agent_run = company_summary(
                model_name=settings.app.company_summary_model,
                api_key=getattr(
                    settings.common,
                    f"{settings.app.company_summary_model.split(':')[0].split('-')[0].upper()}_API_KEY",
                ),
                exchange=state.selected_exchange,
                ticker=state.selected_ticker,
            )
            st.markdown(stream_text(cs_agent_run.output.text_output()))

        state.company_summary = cs_agent_run
        state.messages.append(
            ChatMessage(role="assistant", content=cs_agent_run.output.text_output())
        )
        state.phase = ResearchPhase.QA
        st.rerun()

    # SECTION - QA Chat
    if state.phase is ResearchPhase.QA:
        if user_prompt := st.chat_input("Ask a question about the company…"):
            state.messages.append(ChatMessage(role="user", content=user_prompt))

            with st.chat_message("assistant"):
                company_qa_agent = company_summary_qa(
                    model_name=settings.app.company_summary_qa_model,
                    api_key=getattr(
                        settings.common,
                        f"{settings.app.company_summary_qa_model.split(':')[0].split('-')[0].upper()}_API_KEY",
                    ),
                    company_summary=state.company_summary.output,
                )
                answer = ""
                result = company_qa_agent.run_stream_sync(
                    user_prompt,
                    message_history=result.all_messages()
                    if "result" in locals()
                    else None,
                )
                for token_chunk in result.stream_text(delta=True):
                    answer += token_chunk
                    st.markdown(answer)

            state.messages.append(ChatMessage(role="assistant", content=answer))

            st.rerun()
