from agno.workflow import (
    HumanReview,
    OnError,
    Parallel,
    Step,
    StepInput,
    StepOutput,
    Workflow,
)

from app.agents._definitions import (
    DatasetSelection,
    StrategySelection,
    dataset_resolver,
    strategy_param_resolver,
    strategy_resolver,
)
from app.agents._schema import StrategyParamSelection
from app.utils import async_sqlite_db
from app.workflows._schema import StrategyApplyFinalDraft

from ._helpers import fail_step_output, step_content_check
from ._schema import StrategyApplyLabel

# SECTION - Strategy Apply
dataset_step = Step(
    name=StrategyApplyLabel.dataset.value,
    agent=dataset_resolver,
    human_review=HumanReview(on_error=OnError.pause),
)
strategy_step = Step(
    name=StrategyApplyLabel.strategy.value,
    agent=strategy_resolver,
    human_review=HumanReview(on_error=OnError.pause),
)


def verify_parallel_step_output(step_input: StepInput) -> StepOutput:
    dataset_content = step_content_check(
        step_input.get_step_output(StrategyApplyLabel.dataset.value),
        DatasetSelection,
    )
    if dataset_content is None:
        return fail_step_output(
            f"Dataset selection failed due to {StrategyApplyLabel.dataset.value} step"
        )
    strategy_content = step_content_check(
        step_input.get_step_output(StrategyApplyLabel.strategy.value),
        StrategySelection,
    )
    if strategy_content is None:
        return fail_step_output(
            f"Strategy selection failed due to {StrategyApplyLabel.strategy.value} step"
        )

    for content in (dataset_content, strategy_content):
        if content.needs_clarification:
            return StepOutput(content=content, success=False, stop=True)

    return StepOutput(
        content={
            "strategy_ids": strategy_content.strategy_ids,
        },
        success=True,
    )


async def parameters_selection_step(step_input: StepInput) -> StepOutput:
    param_input = step_content_check(
        step_input.get_step_output(StrategyApplyLabel.strategy.value),
        StrategySelection,
    )
    if param_input is None or not param_input.strategy_ids:
        return fail_step_output(
            f"No strategy IDs available to {StrategyApplyLabel.parameters.value} step"
        )

    strategy_ids = param_input.strategy_ids
    response = await strategy_param_resolver.arun(
        param_input.model_dump_json(include={"strategy_ids"})
    )
    param_selection = response.content
    if not isinstance(param_selection, StrategyParamSelection):
        return fail_step_output(
            "Strategy parameter resolution returned invalid output"
        )
    if param_selection.needs_clarification:
        return StepOutput(content=param_selection, success=False, stop=True)

    resolved_strategy_ids = {
        strategy.strategy_id for strategy in param_selection.strategies
    }
    if resolved_strategy_ids != set(strategy_ids):
        return fail_step_output(
            "Strategy parameter resolution must return parameters for every selected "
            "strategy and no additional strategies"
        )

    return StepOutput(content=param_selection, success=True)


def draft_apply_step(step_input: StepInput) -> StepOutput:
    # check if the param selection step output is available
    param_data = step_content_check(
        step_input.get_step_output(StrategyApplyLabel.parameters.value),
        StrategyParamSelection,
    )
    if param_data is None:
        return fail_step_output(
            f"No strategy parameters available due to {StrategyApplyLabel.parameters.value} step"
        )

    # NOTE - skipping data & strategy resolution steps as they are already completed in the previous step
    dataset_content = step_content_check(
        step_input.get_step_output(StrategyApplyLabel.dataset.value),
        DatasetSelection,
    )
    if dataset_content is None:
        return fail_step_output(
            f"Dataset selection failed due to {StrategyApplyLabel.dataset.value} step"
        )
    strategy_content = step_content_check(
        step_input.get_step_output(StrategyApplyLabel.strategy.value),
        StrategySelection,
    )
    if strategy_content is None:
        return fail_step_output(
            f"Strategy selection failed due to {StrategyApplyLabel.strategy.value} step"
        )

    return StepOutput(
        content=StrategyApplyFinalDraft(
            dataset_id=dataset_content.dataset_id or "",
            dataset_name=dataset_content.dataset_name or "",
            dataset_explanation=dataset_content.explanation,
            strategies=param_data.strategies,
            strategies_explanation=strategy_content.explanation,
        ),
        success=True,
    )


strategy_apply_workflow = Workflow(
    id="strategy-application",
    name=StrategyApplyLabel.workflow.value,
    db=async_sqlite_db,
    steps=[
        # pyrefly: ignore [bad-argument-type]
        Parallel(
            dataset_step, strategy_step, name=StrategyApplyLabel.parallel.value
        ),
        Step(
            name=StrategyApplyLabel.verify_parallel.value,
            executor=verify_parallel_step_output,
            human_review=HumanReview(on_error=OnError.pause),
        ),
        Step(
            name=StrategyApplyLabel.parameters.value,
            executor=parameters_selection_step,
            human_review=HumanReview(on_error=OnError.pause),
        ),
        Step(
            name=StrategyApplyLabel.draft_apply.value,
            executor=draft_apply_step,
            human_review=HumanReview(on_error=OnError.pause),
        ),
    ],
    stream=False,
    debug_mode=True,
)
