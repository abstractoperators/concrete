"""
OpenAI's Structured Outputs integrates directly into Pydantic models using Pydantic's BaseModel class.
Inheriting from this baseclass allows for consistently formatted responses.
Use OpenAI().beta.chat.completions.parse() to generate responses conforming to defined class.

Example:
    class MyClass(BaseModel):
        field1: str
        field2: int

    response = self.client.beta.chat.completions.parse(messages=messages, temperature=self.OPENAI_TEMPERATURE, **kwargs)
    message = response.choices[0].message
    message_formatted: MyClass = message.parsed
"""

from typing import List

from pydantic import Field

from .base import ConcreteBaseModel, KombuMixin


class Response(ConcreteBaseModel):
    pass


class Tool(Response):
    tool_name: str = Field(description="Name of the tool")
    tool_function: str = Field(description="Command to call the tool")
    tool_parameters: list[str] = Field(description="Parameters to pass into the tool function call.")
    tool_keyword_parameters: dict[str, str] = Field(
        description="Parameters specificed by keyword to pass into the tool function call."
    )


class Tools(Response):
    tools: List[Tool] = Field(description="List of tools")


class ProjectFile(Response, KombuMixin):
    file_name: str = Field(description="A file path relative to root")
    file_contents: str = Field(description="The contents of the file")


class ProjectDirectory(Response, KombuMixin):
    project_name: str = Field(description="Name of the project directory")
    files: list[ProjectFile] = Field(
        description="A list of files in the project directory. Each list item represents a file"
    )


class TextResponse(Response, KombuMixin):
    text: str = Field(description="Text response")


class Summary(Response, KombuMixin):
    summary: list[str] = Field(
        description="A list of component summaries. Each list item represents an unbroken summary"
    )


class PlannedComponents(Response, KombuMixin):
    components: list[str] = Field(description="List of planned components")
