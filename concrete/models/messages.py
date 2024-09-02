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

# Tracks all message types created as a sub class of Message
# Keys are not type sensitive
RESPONSE_REGISTRY = {}


class Message(ConcreteModel):
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        registry_name = getattr(cls, '__registry_name__', cls.__name__)
        RESPONSE_REGISTRY[registry_name.lower()] = cls

    @classmethod
    def dereference(cls, name: str):
        """
        Return the object class if it exists otherwise raise a ValueError.
        """
        if not (response_type := RESPONSE_REGISTRY.get(name.lower())):
            raise ValueError(f"Unknown response type: {name}")
        return response_type


class Tool(Message):
    tool_name: str = Field(description="Name of the tool")
    tool_function: str = Field(description="Command to call the tool")
    tool_parameters: list[str] = Field(description="Parameters to pass into the tool function call.")


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
