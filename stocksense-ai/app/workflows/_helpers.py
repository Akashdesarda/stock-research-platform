from typing import TypeVar

from agno.workflow import StepOutput

T = TypeVar("T")


def fail_step_output(message: str = "Step failed") -> StepOutput:
    return StepOutput(content=message, success=False, stop=True)


def step_content_check(output: StepOutput | None, expected_type: type[T]) -> T | None:
    if output is None or not output.success:
        return None
    content = output.content
    return content if isinstance(content, expected_type) else None
