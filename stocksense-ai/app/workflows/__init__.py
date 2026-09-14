import inspect

from agno.workflow import Workflow

from . import _definitions


def _discover_workflow() -> list[Workflow]:
    return [
        obj
        for name, obj in inspect.getmembers(_definitions)
        if isinstance(obj, Workflow) and not name.startswith("_")
    ]


ALL_WORKFLOWS = _discover_workflow()
WORKFLOW_BY_ID = {wf.id: wf for wf in ALL_WORKFLOWS if wf.id is not None}

__all__ = ["ALL_WORKFLOW", "WORKFLOW_BY_ID"]
