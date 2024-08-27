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

from json import dumps
from typing import List

from pydantic import BaseModel, Field


class Response(BaseModel):
    def __str__(self):
        return dumps(self.model_dump(), indent=2).replace("\\n", "\n")

    def __repr__(self):
        return self.__str__()


class Tool(Response):
    tool_name: str = Field(description="Name of the tool")
    tool_call: str = Field(description="Command to call the tool")


class Tools(Response):
    tools: List[Tool] = Field(description="List of tools")


class ProjectFile(Tools):
    file_name: str = Field(description="File path relative to project root")
    file_contents: str = Field(description="File contents")


class ProjectDirectory(Tools):
    project_name: str = Field(description="Name of the project directory")
    files: list[ProjectFile] = Field(description="List of ProjectFiles in the directory")


class TextResponse(Tools):
    text: str = Field(description="Text response")


class Summary(Tools):
    summary: List[str] = Field(description="List of component summaries")


class PlannedComponents(Tools):
    components: List[str] = Field(description="List of planned components")
