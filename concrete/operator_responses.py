from typing import List

from pydantic import BaseModel


class ProjectFile(BaseModel):
    file_name: str
    file_contents: str


class ProjectDirectory(BaseModel):
    files: list[ProjectFile]


class TextResponse(BaseModel):
    text: str


class Summary(BaseModel):
    summary: List[str]


class PlannedComponents(BaseModel):
    components: List[str]
