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

import io
import json
import zipfile

from pydantic import Field

from .base import ConcreteModel

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

    def __str__(self):
        """
        Required for message passing to LMs
        """
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    # TODO: Requires a .schema() method for OpenAI Structured Outputs

    def __repr__(self):
        # Consider moving this to db - don't need a __repr__ unless you're saving it to a db?
        # Consider whether
        pass


class Param(Message):
    name: str = Field(description="Name of the parameter")
    value: str = Field(description="Value of the parameter")


class Tool(Message):
    tool_name: str = Field(description="Name of the tool")
    tool_method: str = Field(description="Command to call the tool")
    tool_parameters: list[Param] = Field(description="List of parameters for the tool")


class ProjectFile(Message):
    file_name: str = Field(description="A file path relative to root")
    file_contents: str = Field(description="The contents of the file")


class ProjectDirectory(Message):
    project_name: str = Field(description="Name of the project directory")
    files: list[ProjectFile] = Field(
        description="A list of files in the project directory. Each list item represents a file"
    )

    def to_zip(self) -> io.BytesIO:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for project_file in self.files:
                zip_file.writestr(project_file.file_name, project_file.file_contents)
        zip_buffer.seek(0)
        return zip_buffer


class TextMessage(Message):
    text: str = Field(description="Text")


class Summary(Message):
    summary: list[str] = Field(
        description="A list of component summaries. Each list item represents an unbroken summary"
    )


class PlannedComponents(Message):
    components: list[str] = Field(description="List of planned components")


class ChildNodeSummary(Message):
    node_name: str = Field(description="Name of the node")
    summary: str = Field(description="Summary of the node")


class NodeSummary(Message):
    node_name: str = Field(description="Name of the node")
    overall_summary: str = Field(description="Summary of the node")
    children_summaries: list[ChildNodeSummary] = Field(description="Brief description of each child node")


class NodeUUID(Message):
    node_uuid: str = Field(description="UUID of the node")
