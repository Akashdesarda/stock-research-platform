from pydantic import BaseModel, Field


class TextToSQLOutput(BaseModel):
    sql_query: str = Field(
        ..., description="Generated DuckDB SQL query based on the user's request"
    )
