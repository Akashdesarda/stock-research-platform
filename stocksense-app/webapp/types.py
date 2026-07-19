from enum import Enum
from typing import Literal

from pydantic import BaseModel


class TickerChoice(Enum):
    index = "Index Based"
    desired = "Desired"
    all = "All"


class RunState(str, Enum):
    idle = "idle"  # no run in flight; ready to send
    generating = "generating"  # streaming in progress -> show STOP
    cancelled = "cancelled"  # user cancelled -> resumable (future)
    error = "error"  # run failed -> retry/resume candidate (future)
    completed = "completed"  # finished cleanly (treated like idle for input)


class TraceStep(BaseModel):
    name: str
    detail: str = ""
    icon: str = "info"
    passed: bool = True


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    steps: list[TraceStep] = []
    steps_open: bool = False
    run_state: str = RunState.idle.value
