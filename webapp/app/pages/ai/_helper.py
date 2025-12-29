import time

import streamlit as st

from app.state.model import ChatMessage


def stream_text(text: str, delay: float = 0.02):
    # sourcery skip: use-fstring-for-concatenation
    for token in text.split():
        yield token + " "
        time.sleep(delay)


# def stream_agent_result(agent: Agent, prompt: str):
#     with agent.run_stream_sync(user_prompt=prompt) as response:
#         for chunk in response.


def render_chat(messages: list[ChatMessage]):
    for msg in messages:
        with st.chat_message(msg.role):
            st.markdown(msg.content)
