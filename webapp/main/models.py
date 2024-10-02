from uuid import UUID

from pydantic import BaseModel


class HiddenInput(BaseModel):
    name: str
    value: str | UUID
