from typing import List

from pydantic import BaseModel


class ProjectFile(BaseModel):
    file_name: str
    file_contents: str

    def __str__(self):
        return f"File Name: {self.file_name}\n" f"File Contents: {self.file_contents}"


class ProjectDirectory(BaseModel):
    files: list[ProjectFile]

    def __str__(self):
        return "Final Files:\n" + "\n\n".join([str(file) for file in self.files])


class TextResponse(BaseModel):
    text: str

    def __str__(self):
        return self.text


class Summary(BaseModel):
    summary: List[str]

    def __str__(self):
        return 'Summary\n' + "\n".join(self.summary)


class PlannedComponents(BaseModel):
    components: List[str]

    def __str__(self):
        return "\n".join([f"[Planned Component]: {component}" for component in self.components])
