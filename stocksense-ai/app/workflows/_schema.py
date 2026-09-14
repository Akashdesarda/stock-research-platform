from enum import Enum

from app.agents._schema import UnitStrategyParameters
from pydantic import BaseModel


class StrategyApplyLabel(Enum):
    dataset = "Dataset Selection"
    strategy = "Strategy Selection"
    parallel = "Parallel Run"
    verify_parallel = "Verify Dataset and Strategy Step"
    parameters = "Parameters Selection"
    draft_apply = "Draft Strategy Apply"
    workflow = "Strategy Application"


class StrategyApplyFinalDraft(BaseModel):
    dataset_id: str
    dataset_name: str
    dataset_explanation: str
    strategies: list[UnitStrategyParameters]
    strategies_explanation: str
