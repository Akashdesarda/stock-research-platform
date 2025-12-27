import streamlit as st

from app.state.model import AppState


class StateManager:
    """
    Typed, centralized Streamlit state manager using Pydantic.
    """

    _SESSION_KEY = "__APP_STATE__"

    @classmethod
    def init(cls) -> AppState:
        """
        Initialize state if missing.
        Safe to call on every rerun and every page.
        """
        if cls._SESSION_KEY not in st.session_state:
            st.session_state[cls._SESSION_KEY] = AppState()
        return st.session_state[cls._SESSION_KEY]

    @classmethod
    def get(cls) -> AppState:
        """
        Get state. Fails loudly if init() was forgotten.
        """
        if cls._SESSION_KEY not in st.session_state:
            raise RuntimeError(
                "StateManager not initialized. Call StateManager.init() first."
            )
        return st.session_state[cls._SESSION_KEY]

    @classmethod
    def reset(cls):
        """Clear all app state (logout / debug use)"""
        st.session_state.pop(cls._SESSION_KEY, None)
