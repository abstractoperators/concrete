from uuid import UUID

from pydantic import BaseModel, Field

from concrete.models.base import ConcreteModel


class MetadataMixin(BaseModel):
    id: UUID


class OperatorBase(ConcreteModel):
    instructions: str = Field(description="Instructions and role of the operator.")
    title: str = Field(description="Title of the operator.")


class OperatorCreate(OperatorBase):
    pass


class Operator(OperatorBase, MetadataMixin):
    class Config:
        from_attributes = True


class OperatorUpdate(ConcreteModel):
    instructions: str | None = Field(description="Instructions and role of the operator.", default=None)
    title: str | None = Field(description="Title of the operator.", default=None)
