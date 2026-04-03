# This module will include all small one time agents
import logging

from openinference.semconv.trace import SpanAttributes
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, AgentRunResult

from stocksense.ai import setup_phoenix_tracing, track_agent_session
from stocksense.ai.skills.context import DatasetDescriptionContextDependency
from stocksense.ai.utils import (
    fetch_prompt_messages,
    get_model,
    render_mustache_conditional_prompt,
)

logger = logging.getLogger("stocksense")

# Phoenix setup
setup_phoenix_tracing()


class DatasetDescriptionOutput(BaseModel):
    name: str = Field(
        ...,
        description="The name of the dataset that must not cross 4 words",
        json_schema_extra={"maxWords": 4},
    )
    description: str = Field(
        ...,
        description="A brief description of the dataset that must not exceed 20 words",
        json_schema_extra={"maxWords": 20},
    )

    @field_validator("name")
    @classmethod
    def name_max_words(cls, v: str) -> str:
        if len(v.split()) > 4:
            raise ValueError("name must not exceed 4 words")
        return v

    @field_validator("description")
    @classmethod
    def description_max_words(cls, v: str) -> str:
        if len(v.split()) > 20:
            raise ValueError("description must not exceed 20 words")
        return v


async def generate_dataset_description(
    context: DatasetDescriptionContextDependency,
    model_name: str,
    api_key: str,
    base_url: str | None = None,
    session_id: str | None = None,
) -> AgentRunResult[DatasetDescriptionOutput]:
    prompt_msgs = await fetch_prompt_messages("dataset-description", context.as_dict())

    # initialize the agent
    agent: Agent[DatasetDescriptionContextDependency, DatasetDescriptionOutput] = Agent(
        model=get_model(model_name, api_key, base_url),
        name="dataset-description",
        deps_type=DatasetDescriptionContextDependency,
        output_type=DatasetDescriptionOutput,
        system_prompt=prompt_msgs[0]["content"],
        instrument=True,
    )

    # Based on the Logical plan customizing the prompt
    if context.sql_query:
        logger.debug("Generating dataset description using SQL query")
        prompt = prompt_msgs[1]["content"]
    else:
        logger.debug("Generating dataset description using dataset metadata")
        # NOTE - This prompt have mustache conditionals that will render the final instruction
        # based on the presence of variables in the context dependency. For example, if interval
        # and period are not provided, it will not include the part of the prompt that talks about them.
        prompt = render_mustache_conditional_prompt(
            template=prompt_msgs[2]["content"], data=context.as_dict()
        )

    if session_id:
        with track_agent_session(
            name="dataset-description",
            session_id=session_id,
            input_prompt=prompt,
            metadata={"model": model_name},  # REVIEW - more metadata to include here?
        ) as span:
            # Running the agent and getting the result
            result = await agent.run(prompt, deps=context)
            try:
                # Adding info to current span for observability
                span.set_attribute(
                    SpanAttributes.OUTPUT_VALUE, result.output.model_dump_json()
                )
            except Exception:
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, str(result.output))
            return result

    # Running the agent and getting the result without tracking if session_id is not provided
    return await agent.run(prompt, deps=context)
