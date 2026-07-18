from enum import Enum
from typing import Literal

from pydantic import BaseModel


class TickerChoice(Enum):
    index = "Index Based"
    desired = "Desired"
    all = "All"


class TraceStep(BaseModel):
    name: str
    detail: str = ""
    icon: str
    passed: bool = True


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    steps: list[TraceStep] = []
    steps_open: bool = False
