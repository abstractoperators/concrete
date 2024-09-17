from uuid import UUID

from pydantic import BaseModel, Field

from concrete.models.base import ConcreteModel


class MetadataMixin(BaseModel):
    id: UUID


class OrmMixin(BaseModel):
    class Config:
        from_attributes = True


class OperatorChildMixin(BaseModel):
    operator_id: UUID
    operator: "Operator"


class OperatorBase(ConcreteModel):
    instructions: str = Field(description="Instructions and role of the operator.")
    title: str = Field(description="Title of the operator.")


class OperatorCreate(OperatorBase):
    pass


class Operator(OperatorBase, MetadataMixin, OrmMixin):
    clients: list["Client"] = []
    tools: list["Tool"] = []


class OperatorUpdate(ConcreteModel):
    instructions: str | None = Field(description="Instructions and role of the operator.", default=None)
    title: str | None = Field(description="Title of the operator.", default=None)


class ClientBase(ConcreteModel):
    client: str = Field(description="Name of LLM client or organization. Defaults to OpenAI", default="OpenAI")
    temperature: float = Field(description="LLM temperature. Defaults to 0.", default=0)
    model: str = Field(description="Model type for LLM. Defaults to gpt-4o-mini", default="gpt-4o-mini")


class Client(ClientBase, MetadataMixin, OrmMixin, OperatorChildMixin):
    pass


class ToolBase(ConcreteModel):
    pass


class Tool(ToolBase, MetadataMixin, OrmMixin, OperatorChildMixin):
    pass


class NodeBase(ConcreteModel):
    """
    Base model for a Node.
    """

    summary: str = Field(description="Summary of the node.")
    domain: str = Field(description="Association of the node.")


class NodeCreate(NodeBase):
    parent_id: UUID | None = Field(default=None, description="ID of the parent node.")  # root has no parent


class Node(NodeBase, MetadataMixin, OrmMixin):
    """
    Full representation of a Node
    """

    id: UUID
    parent_id: int | None = Field(default=None, description="ID of the parent node.")
    children: list["Node"] | None = Field(default_factory=list, description="Child nodes of this node.")


class NodeUpdate(ConcreteModel):
    summary: str | None = Field(default=None, description="Summary of the node.")
    domain: str | None = Field(default=None, description="Domain knowledge association of the node.")
    parent_id: int | None = Field(default=None, description="ID of the parent node.")
