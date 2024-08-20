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

from typing import TypeVar

from pydantic import Field

from .base import ConcreteBaseModel, KombuMixin


class Response(ConcreteBaseModel):
    pass


Response_co = TypeVar('Response_co', bound=Response, covariant=True)


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
