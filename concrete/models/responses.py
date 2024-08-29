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

<<<<<<< HEAD:concrete/operator_responses.py
import json
from typing import List
=======
from pydantic import Field
>>>>>>> ab723e0 (AbstractOperator Base Class, ConcreteBaseModel, Celery integration (#29)):concrete/models/responses.py

from .base import ConcreteBaseModel, KombuMixin


<<<<<<< HEAD:concrete/operator_responses.py
class Response(BaseModel):
    def __str__(self):
        # Remove tools from output if empty to improve prompt chaining quality.
        # Unfortunately, still affected by nesting of tools.
        model_dict = self.model_dump(mode='json', exclude_unset=True, exclude_none=True)
        if not model_dict.get("tools"):
            model_dict.pop("tools", None)

        # I give up on finding a better way to format this string.
        # f'{model_str} doesn't work
        # re.sub is more elegant, but its basically the same thing
        model_str = (
            json.dumps(model_dict, indent=4)
            .replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\'", "\'")
            .replace('\\"', '\"')
        )

        return model_str

    def __repr__(self):
        model_dict = self.model_dump(mode='json', exclude_unset=True, exclude_none=True)
        return json.dumps(model_dict, indent=4)


class Tool(Response):
    tool_name: str = Field(description="Name of the tool")
    tool_call: str = Field(description="Command to call the tool")


class Tools(Response):
    tools: List[Tool] = Field(description="List of tools")


class ProjectFile(Tools):
    file_name: str = Field(description="A file path relative to root")
    file_contents: str = Field(description="The contents of the file")


class ProjectDirectory(Tools):
    project_name: str = Field(description="Name of the project directory")
    files: list[ProjectFile] = Field(
        description="A list of files in the project directory. Each list item represents a file"
    )


class TextResponse(Tools):
    text: str = Field(description="Text response")


class Summary(Tools):
    summary: List[str] = Field(
        description="A list of component summaries. Each list item represents an unbroken summary"
    )


class PlannedComponents(Tools):
    components: List[str] = Field(description="List of planned components")
=======
class Response(ConcreteBaseModel):
    pass


class ProjectFile(Response, KombuMixin):
    file_name: str = Field(description="File path relative to project root")
    file_contents: str = Field(description="File contents")


class ProjectDirectory(Response, KombuMixin):
    files: list[ProjectFile] = Field(description="List of ProjectFiles in the directory")


class TextResponse(Response, KombuMixin):
    text: str = Field(description="Text response")


class Summary(Response, KombuMixin):
    summary: list[str] = Field(description="List of component summaries")


class PlannedComponents(Response, KombuMixin):
    components: list[str] = Field(description="List of planned components")
>>>>>>> ab723e0 (AbstractOperator Base Class, ConcreteBaseModel, Celery integration (#29)):concrete/models/responses.py
