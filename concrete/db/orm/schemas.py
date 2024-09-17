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


# Nodes for knowledge graph
class NodeBase(ConcreteModel):
    summary: str = Field(description="A summary of the associated domain knowledge")
    assoc: str = Field(description="Domain knowledge the node summary is associated with")
    parents: list["Node"] = Field(description="Parent nodes of this node", default=[])
    children: list["Node"] = Field(description="Child nodes of this node", default=[])


class Node(NodeBase, MetadataMixin, OrmMixin):
    pass


class NodeCreate(Node):
    pass


class NodeUpdate(ConcreteModel):
    pass
