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
# Allowed primitives
https://platform.openai.com/docs/guides/structured-outputs/supported-schemas
The following types are supported for Structured Outputs:
String, Number, Boolean, Integer, Object, Array, Enum, anyOf

Optional is not allowed with OpenAI Structured Outputs. All fields must be required.
"""

from pydantic import Field

from .base import ConcreteModel, KombuMixin

# Tracks all message types created as a sub class of Message
# Keys are not type sensitive
MESSAGE_REGISTRY = {}


class Message(ConcreteModel):
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        registry_name = getattr(cls, "__registry_name__", cls.__name__)
        MESSAGE_REGISTRY[registry_name.lower()] = cls

    @classmethod
    def dereference(cls, name: str):
        """
        Return the object class if it exists otherwise raise a ValueError.
        """
        if not (message_type := MESSAGE_REGISTRY.get(name.lower())):
            raise ValueError(f"Unknown response type: {name}")
        return message_type


class Tool(Message):
    tool_name: str = Field(description="Name of the tool")
    tool_function: str = Field(description="Command to call the tool")
    tool_parameters: list[str] = Field(description="Parameters to pass into the tool function call.")


class Tools(Message):
    tools: list[Tool] = Field(description="List of tools")


# N.B. KombuMixin must be added to each leaf child node class due to serializer registration
class ProjectFile(Message, KombuMixin):
    file_name: str = Field(description="A file path relative to root")
    file_contents: str = Field(description="The contents of the file")


class ProjectDirectory(Message, KombuMixin):
    project_name: str = Field(description="Name of the project directory")
    files: list[ProjectFile] = Field(
        description="A list of files in the project directory. Each list item represents a file"
    )


class TextMessage(Message, KombuMixin):
    text: str = Field(description="Text")


class Summary(Message, KombuMixin):
    summary: list[str] = Field(
        description="A list of component summaries. Each list item represents an unbroken summary"
    )


class PlannedComponents(Message, KombuMixin):
    components: list[str] = Field(description="List of planned components")
