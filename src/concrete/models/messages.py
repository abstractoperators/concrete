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
from dataclasses import Field, dataclass, field, fields
from typing import Any, Dict, List, Union, get_args, get_origin

from ..utils import map_python_type_to_json_type
from .base import ConcreteModel

# Tracks all message types created as a sub class of Message
# Keys are not type sensitive
MESSAGE_REGISTRY = {}


@dataclass
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
        pass

    @classmethod
    def as_response_format(cls) -> dict:
        """
        Converts the dataclass into a JSON schema dictionary compatible with OpenAI's structured outputs.
        """
        return {
            'type': 'json_schema',
            'json_schema': {
                'name': cls.__name__,
                'description': cls.__doc__,
                'strict': True,
                'schema': {
                    'type': 'object',
                    'properties': cls.properties(),
                    'required': [field_.name for field_ in fields(cls)],
                    'additionalProperties': False,
                },
            },
        }

    @classmethod
    def properties(cls) -> dict:
        """
        Returns dict properties
        """

        def type_to_property(type_) -> dict:
            # Converts a field into a field_name: {type: field_type... optional[items, properties]}
            # Fields can have complex types like list[dict[str, str]], which need to be handled recursively
            # Additionally, the field can be another Message model.
            # Base Case: Primitive one-to-one mappings

            # Base Cases:
            match type_:  # Does python pattern matching even hash anything. Is this just a glorifiied if else?
                case t if t is str:
                    return {'type': 'string'}
                case t if t is int:
                    return {'type': 'integer'}
                case t if t is float:
                    return {'type': 'number'}
                case t if t is bool:
                    return {'type': 'boolean'}
                case t if issubclass(t, Message):
                    return {
                        'type': 'object',
                        'properties': t.properties(),
                        'required': [field_.name for field_ in fields(t)],
                        'additionalProperties': False,
                    }
            # Recursive Cases
            origin = get_origin(type_)
            # TODO: Handle AnyOf, Enum, Dict
            if origin is list:
                item_type = get_args(type_)[0]
                return {'type': 'array', 'items': type_to_property(item_type)}

        properties = {}
        for field_ in fields(cls):
            field_type = field_.type
            properties[field_.name] = type_to_property(field_type)

        return properties


@dataclass
class TextMessage(Message):
    text: str = field()


@dataclass
class Param(Message):
    name: str = field(metadata={'description': 'Name of the parameter'})
    value: str = field(metadata={'description': 'Value of the parameter'})


@dataclass
class Tool(Message):
    tool_name: str = field(metadata={'description': 'Name of the tool'})
    tool_method: str = field(metadata={'description': 'Command to call the tool'})
    tool_parameters: list[Param] = field(metadata={'description': 'List of parameters for the tool'})


@dataclass
class PlannedComponents(Message):
    components: list[str]


@dataclass
class Summary(Message):
    summary: list[str] = field(
        metadata={'description': 'A list of component summaries. Each list item represents an unbroken summary'}
    )


@dataclass
class ProjectFile(Message):
    file_name: str = field(metadata={'description': 'A file path relative to root'})
    file_contents: str = field(metadata={'description': 'The contents of the file'})


@dataclass
class ProjectDirectory(Message):
    project_name: str = field(metadata={'description': 'Name of the project directory'})
    files: list[ProjectFile] = field(
        metadata={'description': 'A list of files in the project directory. Each list item represents a file'}
    )


@dataclass
class Param:
    pass


@dataclass
class NodeUUID:
    pass


@dataclass
class NodeSummary:
    pass


@dataclass
class ChildNodeSummary:
    pass


# class Param(Message):
#     name: str = Field(description="Name of the parameter")
#     value: str = Field(description="Value of the parameter")


# class Tool(Message):
#     tool_name: str = Field(description="Name of the tool")
#     tool_method: str = Field(description="Command to call the tool")
#     tool_parameters: list[Param] = Field(description="List of parameters for the tool")


# class ProjectFile(Message):
#     file_name: str = Field(description="A file path relative to root")
#     file_contents: str = Field(description="The contents of the file")


# class ProjectDirectory(Message):
#     project_name: str = Field(description="Name of the project directory")
#     files: list[ProjectFile] = Field(
#         description="A list of files in the project directory. Each list item represents a file"
#     )

#     def to_zip(self) -> io.BytesIO:
#         zip_buffer = io.BytesIO()
#         with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#             for project_file in self.files:
#                 zip_file.writestr(project_file.file_name, project_file.file_contents)
#         zip_buffer.seek(0)
#         return zip_buffer


# class TextMessage(Message):
#     text: str = Field(description="Text")


# class Summary(Message):
#     summary: list[str] = Field(
#         description="A list of component summaries. Each list item represents an unbroken summary"
#     )


# class PlannedComponents(Message):
#     components: list[str] = Field(description="List of planned components")


# class ChildNodeSummary(Message):
#     node_name: str = Field(description="Name of the node")
#     summary: str = Field(description="Summary of the node")


# class NodeSummary(Message):
#     node_name: str = Field(description="Name of the node")
#     overall_summary: str = Field(description="Summary of the node")
#     children_summaries: list[ChildNodeSummary] = Field(description="Brief description of each child node")


# class NodeUUID(Message):
#     node_uuid: str = Field(description="UUID of the node")
