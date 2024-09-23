from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from ...state import ProjectStatus
from .setup import engine


class Base(SQLModel):
    def __repr__(self) -> str:
        return self.model_dump_json(indent=4, exclude_unset=True, exclude_none=True)


class MetadataMixin(SQLModel):
    id: UUID = Field(primary_key=True, default_factory=uuid4)


# Relationship Models


class OperatorToolLink(Base, table=True):
    operator_id: UUID = Field(foreign_key="operator.id", primary_key=True)
    tool_id: UUID = Field(foreign_key="tool.id", primary_key=True)


# Orchestrator Models


class OrchestratorBase(Base):
    type_name: str = Field(description="type of orchestrator", max_length=32)
    title: str = Field(description="Title of the orchestrator.", max_length=32)
    owner: str = Field(description="name of owner", max_length=32)


class OrchestratorUpdate(Base):
    title: str | None = Field(
        description="Title of the orchestrator.",
        max_length=32,
        default=None,
    )
    owner: str | None = Field(
        description="name of owner",
        max_length=32,
        default=None,
    )


class OrchestratorCreate(OrchestratorBase):
    pass


class Orchestrator(OrchestratorBase, MetadataMixin, table=True):
    operators: list["Operator"] = Relationship(
        back_populates="orchestrator",
        cascade_delete=True,
    )


# Operator Models


class OperatorBase(Base):
    instructions: str = Field(description="Instructions and role of the operator.")
    title: str = Field(description="Title of the operator.", max_length=32)
    orchestrator_id: UUID = Field(
        description="ID of Orchestrator that owns this client.",
        foreign_key="orchestrator.id",
        ondelete="CASCADE",
    )


class OperatorUpdate(Base):
    instructions: str | None = Field(description="Instructions and role of the operator.", default=None)
    title: str | None = Field(description="Title of the operator.", max_length=32, default=None)


class OperatorCreate(OperatorBase):
    pass


# TODO: data models with pseudo-relationships
# https://sqlmodel.tiangolo.com/tutorial/fastapi/relationships/#data-models-without-relationship-attributes
class Operator(OperatorBase, MetadataMixin, table=True):
    clients: list["Client"] = Relationship(
        back_populates="operator",
        cascade_delete=True,
    )
    tools: list["Tool"] = Relationship(back_populates="operators", link_model=OperatorToolLink)
    orchestrator: "Orchestrator" = Relationship(back_populates="operators")


# Client Models


class ClientBase(Base):
    client: str = Field(
        description="Name of LLM client or organization. Defaults to OpenAI",
        default="OpenAI",
        max_length=32,
    )  # TODO: change to more constrained type once use case is better understood
    temperature: float = Field(description="LLM temperature. Defaults to 0.", default=0)
    model: str = Field(
        description="Model type for LLM. Defaults to gpt-4o-mini",
        default="gpt-4o-mini",
        max_length=32,
    )

    orchestrator_id: UUID = Field(
        description="ID of Orchestrator that owns the Operator of this client.",
        foreign_key="orchestrator.id",
    )
    operator_id: UUID = Field(
        description="ID of Operator that owns this client.",
        foreign_key="operator.id",
        ondelete="CASCADE",
    )


class ClientUpdate(Base):
    client: str | None = Field(
        description="Name of LLM client or organization",
        default=None,
        max_length=32,
    )  # TODO: change to more constrained type once use case is better understood
    temperature: float | None = Field(description="LLM temperature", default=None)
    model: str | None = Field(
        description="Model type for LLM.",
        default=None,
        max_length=32,
    )


class ClientCreate(ClientBase):
    pass


# TODO: data models with pseudo-relationships
class Client(ClientBase, MetadataMixin, table=True):
    operator: Operator = Relationship(back_populates="clients")


# Tool Models


# May want Enum here to restrict to Predefined tools
class ToolBase(Base):
    pass


class ToolUpdate(Base):
    pass


class ToolCreate(ToolBase):
    pass


class Tool(ToolBase, MetadataMixin, table=True):
    operators: list[Operator] = Relationship(back_populates="tools", link_model=OperatorToolLink)


# Message Models


class MessageBase(Base):
    type_name: str = Field(description="type of message")
    content: str = Field(description="Content of message as JSON dump")
    prompt: str | None = Field(
        description="Initial prompt for the thread this message belongs to.",
        default=None,
    )
    status: ProjectStatus = ProjectStatus.INIT

    orchestrator_id: UUID = Field(
        description="ID of Orchestrator that owns this client.",
        foreign_key="orchestrator.id",
        ondelete="CASCADE",
    )


class MessageUpdate(Base):
    status: ProjectStatus | None = None


class MessageCreate(MessageBase):
    pass


class Message(MessageBase, MetadataMixin, table=True):
    pass


# Knowledge Graph Models


class NodeBase(Base):
    """
    Base model for a Node.
    """

    parent_id: UUID | None = Field(
        default=None,
        description="ID of the parent node.",
        foreign_key="node.id",
        ondelete="CASCADE",
    )


class NodeUpdate(Base):
    parent_id: UUID | None = Field(
        default=None,
        description="ID of the parent node.",
        foreign_key="node.id",
        ondelete="CASCADE",
    )


class NodeCreate(NodeBase):
    pass


class Node(NodeBase, MetadataMixin, table=True):
    children: list["Node"] = Relationship(
        back_populates="parent",
        cascade_delete=True,
    )
    parent: Optional["Node"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "node.c.id"},
    )


# Figure out an elegant solution to inherit from Node
# https://github.com/fastapi/sqlmodel/issues/488
# https://docs.sqlalchemy.org/en/20/orm/inheritance.html
# https://docs.sqlalchemy.org/en/20/orm/self_referential.html
# https://docs.sqlalchemy.org/en/20/_modules/examples/adjacency_list/adjacency_list.html

# Inheritance might be bad
# https://sqlmodel.tiangolo.com/tutorial/fastapi/multiple-models/#docs-ui-with-hero-responses
# https://sqlmodel.tiangolo.com/tutorial/fastapi/relationships/#models-with-relationships


class RepoNodeBase(Base):
    org: str = Field(description="Organization to which the repo belongs.", index=True)
    repo: str = Field(description="Repository name.", index=True)
    partition_type: str = Field(description="Type of the node. directory/file/chunk")
    name: str = Field(description="Name of the chunk. eg README.md, module.py/func_foo")
    summary: str = Field(description="Summary of the node.")
    parent_id: UUID | None = Field(
        default=None,
        description="ID of the parent node.",
        foreign_key="reponode.id",
        ondelete="CASCADE",
    )
    abs_path: str = Field(description="")


class RepoNodeUpdate(NodeUpdate):
    org: str | None = Field(description="Organization to which the repo belongs.", default=None)
    repo: str | None = Field(description="Repository name.", default=None)
    type: str | None = Field(description="Type of the node. directory/file/chunk", default=None)
    name: str | None = Field(description="Name of the chunk. eg README.md, module.py/func_foo", default=None)
    summary: str | None = Field(description="Summary of the node.", default=None)
    abs_path: str | None = Field(description="", default=None)


class RepoNodeCreate(RepoNodeBase):
    pass


class RepoNode(RepoNodeBase, MetadataMixin, table=True):
    children: list["RepoNode"] = Relationship(
        back_populates="parent",
        cascade_delete=True,
    )
    parent: Optional["RepoNode"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "reponode.c.id"},
    )


SQLModel.metadata.create_all(bind=engine)
