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
    parent_id: UUID | None = Field(default=None, description="ID of the parent node.")  # root has no parent


class NodeCreate(NodeBase):
    pass


class NodeUpdate(ConcreteModel):
    summary: str | None = Field(default=None, description="Summary of the node.")
    parent_id: int | None = Field(default=None, description="ID of the parent node.")


class RepoNode(NodeBase):
    org: str = Field(description="Organization to which the repo belongs.")
    repo: str = Field(description="Repository name.")
    type: str = Field(description="Type of the node. directory/file/chunk")
    name: str = Field(description="Name of the chunk. eg README.md, module.py/func_foo")  # idk yet
    summary: str = Field(description="Summary of the node.")


class RepoNodeUpdate(NodeUpdate):
    org: str | None = Field(description="Organization to which the repo belongs.")
    repo: str | None = Field(description="Repository name.")
    type: str | None = Field(description="Type of the node. directory/file/chunk")
    name: str | None = Field(description="Name of the chunk. eg README.md, module.py/func_foo")  # idk yet
    summary: str | None = Field(description="Summary of the node.")


class RepoNodeCreate(RepoNode):
    pass
