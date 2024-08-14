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

from pydantic import BaseModel


class Response(BaseModel):
    def __str__(self):
        return dumps(self.model_dump(), indent=2)

    def __repr__(self):
        return self.__str__()


class ProjectFile(Response):
    file_name: str
    file_contents: str


class ProjectDirectory(Response):
    files: list[ProjectFile]


class TextResponse(Response):
    text: str


class Summary(Response):
    summary: List[str]


class PlannedComponents(Response):
    components: List[str]
