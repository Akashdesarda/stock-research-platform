from pydantic import BaseModel, Field, field_validator


class TextToSQLOutput(BaseModel):
    sql_query: str = Field(
        ..., description="Generated DuckDB SQL query based on the user's request"
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
