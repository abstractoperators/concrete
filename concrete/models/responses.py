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

from typing import List, Optional

from pydantic import Field

from .base import ConcreteModel, KombuMixin

RESPONSE_REGISTRY = {}


class Message(ConcreteModel):
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        registry_name = getattr(cls, '__registry_name__', cls.__name__)
        RESPONSE_REGISTRY[registry_name] = cls


def get_response_type(name: str):
    response_type = RESPONSE_REGISTRY.get(name.lower())
    if response_type is None:
        raise ValueError(f"Unknown response type: {name}")
    return response_type


class Tool(Message):
    tool_name: str = Field(description="Name of the tool")
    tool_function: str = Field(description="Command to call the tool")
    tool_parameters: Optional[list[str]] = Field(None, description="Parameters to pass into the tool function call.")
    tool_keyword_parameters: Optional[dict[str, str]] = Field(
        None, description="Parameters specificed by keyword to pass into the tool function call."
    )


class Tools(Message):
    tools: List[Tool] = Field(description="List of tools")


class ProjectFile(Message, KombuMixin):
    file_name: str = Field(description="A file path relative to root")
    file_contents: str = Field(description="The contents of the file")


class ProjectDirectory(Message, KombuMixin):
    project_name: str = Field(description="Name of the project directory")
    files: list[ProjectFile] = Field(
        description="A list of files in the project directory. Each list item represents a file"
    )


class TextMessage(Message, KombuMixin):
    text: str = Field(description="Text response")


class Summary(Message, KombuMixin):
    summary: list[str] = Field(
        description="A list of component summaries. Each list item represents an unbroken summary"
    )


class PlannedComponents(Message, KombuMixin):
    components: list[str] = Field(description="List of planned components")
