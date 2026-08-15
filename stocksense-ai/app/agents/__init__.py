import inspect

from agno.agent import Agent

from . import _definitions


def _discover_agents() -> list[Agent]:
    return [
        obj
        for name, obj in inspect.getmembers(_definitions)
        if isinstance(obj, Agent) and not name.startswith("_")
    ]


ALL_AGENTS = _discover_agents()
AGENTS_BY_ID = {agent.id: agent for agent in ALL_AGENTS if agent.id is not None}

__all__ = ["AGENTS_BY_ID", "ALL_AGENTS"]
