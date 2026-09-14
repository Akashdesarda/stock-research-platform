from pydantic import BaseModel, Field, field_validator, model_validator


class TextToSQLOutput(BaseModel):
    sql_query: str = Field(
        ...,
        description="Generated DuckDB SQL query based on the user's request",
    )


class DatasetDescriptionOutput(BaseModel):
    # """Output schema for dataset description generation.

    # Attributes
    # ----------
    # name : str
    #     The name of the dataset (maximum 4 words)
    # description : str
    #     A brief description of the dataset (maximum 20 words)
    # """
    name: str = Field(
        ...,
        description="The name of the dataset that must not exceed 4 words",
        json_schema_extra={"maxWords": 4},
    )
    description: str = Field(
        ...,
        description="A brief description of the dataset that must not exceed 20 words",
        json_schema_extra={"maxWords": 20},
    )

    @field_validator("name")
    @classmethod
    def validate_name_word_count(cls, v: str) -> str:
        """Validate that name does not exceed 4 words."""
        if len(v.split()) > 4:
            raise ValueError("name must not exceed 4 words")
        return v

    @field_validator("description")
    @classmethod
    def validate_description_word_count(cls, v: str) -> str:
        """Validate that description does not exceed 20 words."""
        if len(v.split()) > 20:
            raise ValueError("description must not exceed 20 words")
        return v


class SessionTitleOutput(BaseModel):
    title: str = Field(
        ...,
        description="A title for the session that must not exceed 5 words",
        json_schema_extra={"maxWords": 5},
    )

    @field_validator("title")
    @classmethod
    def validate_title_word_count(cls, v: str) -> str:
        """Validate that title does not exceed 5 words."""
        if len(v.split()) > 5:
            raise ValueError("title must not exceed 5 words")
        return v


class DatasetSelection(BaseModel):
    dataset_id: str | None = Field(
        None,
        description="The unique identifier of the selected dataset from the registered dataset list",
    )
    dataset_name: str | None = Field(
        None,
        description="The name of the selected dataset from the registered dataset list",
    )
    needs_clarification: bool = Field(
        False,
        description="Indicates whether clarification is needed for the dataset selection",
    )
    clarification_question: str | None = Field(
        None,
        description="The clarification question to ask if clarification is needed",
    )
    explanation: str = Field(..., description="The explanation for the selection")

    @model_validator(mode="after")
    def validate_clarification(self):
        """Validate that clarification question is provided when clarification is needed."""
        if self.needs_clarification:
            if self.dataset_id:
                raise ValueError(
                    "dataset_id must be empty when clarification is needed"
                )
            if self.dataset_name:
                raise ValueError(
                    "dataset_name must be empty when clarification is needed"
                )
            if self.clarification_question:
                raise ValueError(
                    "clarification_question must be provided when needs_clarification is True"
                )
        elif not self.dataset_id or not self.dataset_name:
            raise ValueError(
                "dataset_id and dataset_name must be provided when clarification is not needed"
            )
        return self


class StrategySelection(BaseModel):
    strategy_ids: list[str] = Field(
        default_factory=list,
        description="The list of selected strategy IDs based on the user's request",
    )
    needs_clarification: bool = Field(
        False,
        description="Indicates whether clarification is needed for the selection",
    )
    clarification_question: str | None = Field(
        None,
        description="The clarification question to ask if clarification is needed",
    )
    explanation: str = Field(..., description="The explanation for the selection")

    @model_validator(mode="after")
    def validate_strategy_selection(self):
        if self.needs_clarification:
            if self.strategy_ids:
                raise ValueError(
                    "strategy_ids must be empty when clarification is needed"
                )
            if self.clarification_question is None:
                raise ValueError(
                    "clarification_question is required when clarification is needed"
                )
        elif not self.strategy_ids:
            raise ValueError(
                "strategy_ids must not be empty when clarification is not needed"
            )

        return self


class StrategyParameter(BaseModel):
    name: str = Field(
        ..., description="The parameter name defined by the selected strategy"
    )
    value: str | int | float | bool | None = Field(
        ...,
        description="The resolved parameter value, or null when unavailable",
    )


class UnitStrategyParameters(BaseModel):
    strategy_id: str = Field(
        ..., description="The unique identifier of the selected strategy"
    )
    parameters: list[StrategyParameter] = Field(
        ..., description="The resolved parameters for this strategy"
    )


class StrategyParamSelection(BaseModel):
    strategies: list[UnitStrategyParameters] = Field(
        ...,
        description="The list of strategies with their resolved parameters",
    )
    needs_clarification: bool = Field(
        False,
        description="Indicates whether clarification is needed for the selection",
    )
    clarification_question: str | None = Field(
        None,
        description="The clarification question to ask if clarification is needed",
    )
    explanation: str = Field(..., description="The explanation for the selection")

    @model_validator(mode="after")
    def validate_draft(self):
        if self.needs_clarification:
            if not self.clarification_question:
                raise ValueError(
                    "clarification_question is required when clarification is needed"
                )
        elif not self.strategies:
            raise ValueError(
                "strategies must not be empty when clarification is not needed"
            )

        return self
