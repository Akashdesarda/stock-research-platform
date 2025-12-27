from typing import Type, TypeVar

import streamlit as st
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StateManager:
    """
    Page-scoped, typed Streamlit state manager.
    """

    _ROOT_KEY = "__STATE__"

    @classmethod
    def _root(cls) -> dict:
        if cls._ROOT_KEY not in st.session_state:
            st.session_state[cls._ROOT_KEY] = {}
        return st.session_state[cls._ROOT_KEY]

    @classmethod
    def init(cls, page_key: str, model: Type[T]) -> T:
        """
        Initialize state for a specific page.
        Safe to call on every rerun.
        """
        root = cls._root()

        if page_key not in root:
            root[page_key] = model()

        return root[page_key]

    @classmethod
    def get(cls, page_key: str, model: Type[T]) -> T:
        """
        Get state for a page. Fails loudly if not initialized.
        """
        root = cls._root()

        if page_key not in root:
            raise RuntimeError(
                f"State for page '{page_key}' not initialized. "
                f"Call StateManager.init('{page_key}', {model.__name__}) first."
            )

        state = root[page_key]
        if not isinstance(state, model):
            raise TypeError(f"State for '{page_key}' is not of type {model.__name__}")

        return state

    @classmethod
    def reset(cls, page_key: str):
        cls._root().pop(page_key, None)
