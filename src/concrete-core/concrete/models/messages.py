"""
https://platform.openai.com/docs/guides/structured-outputs/supported-schemas
The following types are supported for Structured Outputs:
String, Number, Boolean, Integer, Object, Array, Enum, anyOf
Use OpenAI().beta.chat.completions.parse() to generate responses conforming to defined class.

Example:
    class Fruit(Message):
        name: str = field(metadata={'description': 'Name of the fruit'})
        
    response = self.client.beta.chat.completions.parse(messages=messages, temperature=self.OPENAI_TEMPERATURE, response_format=Fruit.as_response_format()) # noqa
    
    message = response.choices[0].message
    message_formatted: MyClass = message.parsed
"""

import json

from pydantic import Field

from .base import ConcreteModel

# Tracks all message types created as a sub class of Message
# Keys are not type sensitive
MESSAGE_REGISTRY: dict[str, "Message"] = {}


class Message(ConcreteModel):
    """
    Wrapper for OpenAI Structured Outputs
    """

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

    def __repr__(self):
        # Consider moving this to db - don't need a __repr__ unless you're saving it to a db?
        # Consider whether
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class TextMessage(Message):
    text: str = Field()


class Param(Message):
    name: str = Field(description="Name of the parameter")
    value: str = Field(description="Value of the parameter")


class Tool(Message):
    tool_name: str = Field(description="Name of the tool")
    tool_method: str = Field(description="Command to call the tool")
    tool_parameters: list[Param] = Field(description="List of parameters for the tool")


class PlannedComponents(Message):
    components: list[str] = Field(description="List of planned components")


class Summary(Message):
    summary: list[str] = Field(
        description="A list of component summaries. Each list item represents an unbroken summary"
    )


class ProjectFile(Message):
    file_name: str = Field(description="A file path relative to root")
    file_contents: str = Field(description="The contents of the file")


class ProjectDirectory(Message):
    project_name: str = Field(description="Name of the project directory")
    files: list[ProjectFile] = Field(
        description="A list of files in the project directory. Each list item represents a file"
    )


class ChildNodeSummary(Message):
    node_name: str = Field(description="Name of the node")
    summary: str = Field(description="Summary of the node")


class NodeSummary(Message):
    node_name: str = Field(description="Name of the node")
    overall_summary: str = Field(description="Summary of the node")
    children_summaries: list[ChildNodeSummary] = Field(description="Brief description of each child node")


class NodeUUID(Message):
    node_uuid: str = Field(description="UUID of the node")
