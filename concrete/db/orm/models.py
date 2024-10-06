from typing import Optional, Self
from uuid import UUID, uuid4

from pydantic import ValidationError, model_validator
from sqlalchemy import CheckConstraint
from sqlalchemy.schema import Index
from sqlmodel import Field, Relationship, SQLModel

from ...state import ProjectStatus
from .setup import engine


class Base(SQLModel):
    def __repr__(self) -> str:
        return self.model_dump_json(indent=4, exclude_unset=True, exclude_none=True)


class MetadataMixin(SQLModel):
    id: UUID = Field(primary_key=True, default_factory=uuid4)


class ProfilePictureMixin(SQLModel):
    profile_picture_url: str | None = Field(
        description="URL leading to profile picture of sender.",
        default=None,
    )  # TODO: probably use urllib here, oos


# Relationship Models


class OperatorToolLink(Base, table=True):
    operator_id: UUID = Field(foreign_key="operator.id", primary_key=True)
    tool_id: UUID = Field(foreign_key="tool.id", primary_key=True)


# User Models


class UserBase(Base, ProfilePictureMixin):
    pass


class UserUpdate(Base, ProfilePictureMixin):
    pass


class UserCreate(UserBase):
    pass


class User(UserBase, MetadataMixin, table=True):
    pass


# Orchestrator Models


class OrchestratorBase(Base):
    # TODO turn into enum
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
    projects: list["Project"] = Relationship(
        back_populates="orchestrator",
        cascade_delete=True,
    )


# Operator Models


class OperatorBase(Base, ProfilePictureMixin):
    instructions: str = Field(description="Instructions and role of the operator.")
    title: str = Field(description="Title of the operator.", max_length=32)

    orchestrator_id: UUID = Field(
        description="ID of Orchestrator that owns this operator.",
        foreign_key="orchestrator.id",
        ondelete="CASCADE",
    )


class OperatorUpdate(Base, ProfilePictureMixin):
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
    orchestrator: Orchestrator = Relationship(back_populates="operators")

    direct_message_project: "Project" = Relationship(
        back_populates="direct_message_operator",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "Project.direct_message_operator_id",
        },
    )


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


# Project Models


class ProjectBase(Base):
    title: str = Field(description="Title of the project.", max_length=64)
    orchestrator_id: UUID = Field(
        description="ID of Orchestrator that owns this project.",
        foreign_key="orchestrator.id",
        ondelete="CASCADE",
    )

    executive_id: UUID | None = Field(
        description="ID of executive operator for this project.",
        foreign_key="operator.id",
        default=None,
    )
    developer_id: UUID | None = Field(
        description="ID of developer operator for this project.",
        foreign_key="operator.id",
        default=None,
    )


class ProjectUpdate(Base):
    title: str | None = Field(description="Title of the project.", max_length=32, default=None)

    executive_id: UUID | None = Field(
        description="ID of executive operator for this project.",
        foreign_key="operator.id",
        default=None,
    )
    developer_id: UUID | None = Field(
        description="ID of developer operator for this project.",
        foreign_key="operator.id",
        default=None,
    )


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase, MetadataMixin, table=True):
    orchestrator: Orchestrator = Relationship(back_populates="projects")

    direct_message_operator_id: UUID | None = Field(
        description="ID of operator that owns this project IF it is a direct message project.",
        foreign_key="operator.id",
        unique=True,
        ondelete="CASCADE",
    )
    direct_message_operator: Operator | None = Relationship(
        back_populates="direct_message_project",
        sa_relationship_kwargs={
            "foreign_keys": "Project.direct_message_operator_id",
            "single_parent": True,
        },
    )

    executive: Operator | None = Relationship(sa_relationship_kwargs={"foreign_keys": "Project.executive_id"})
    developer: Operator | None = Relationship(sa_relationship_kwargs={"foreign_keys": "Project.developer_id"})

    messages: list["Message"] = Relationship(back_populates="project", cascade_delete=True)


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

    project_id: UUID = Field(
        description="ID of Project that owns this message.",
        foreign_key="project.id",
        ondelete="CASCADE",
    )

    user_id: UUID | None = Field(
        description="ID of this message's sender if it's a user.",
        foreign_key="user.id",
        default=None,
    )
    operator_id: UUID | None = Field(
        description="ID of this message's sender if it's an operator.",
        foreign_key="operator.id",
        default=None,
    )

    @model_validator(mode="after")
    def check_operator_xor_user(self) -> Self:
        if not (bool(self.operator_id) is not bool(self.user_id)):
            raise ValidationError("The sender can only be one entity!")
        return self

    __table_args__ = (
        CheckConstraint("(operator_id IS NULL <> user_id IS NULL)", name="The sender can only be one entity!"),
    )


class MessageUpdate(Base):
    status: ProjectStatus | None = None


class MessageCreate(MessageBase):
    pass


class Message(MessageBase, MetadataMixin, table=True):
    project: Project = Relationship(back_populates="messages")
    user: User | None = Relationship()
    operator: Operator | None = Relationship()


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
    children_summaries: str = Field(description="Brief summary of each child node.")
    parent_id: UUID | None = Field(
        default=None,
        description="ID of the parent node.",
        foreign_key="reponode.id",
        ondelete="CASCADE",
    )
    abs_path: str = Field(description="")
    branch: str = Field(description="Branch of the repo.", index=True)


class RepoNodeUpdate(NodeUpdate):
    org: str | None = Field(description="Organization to which the repo belongs.", default=None)
    repo: str | None = Field(description="Repository name.", default=None)
    type: str | None = Field(description="Type of the node. directory/file/chunk", default=None)
    name: str | None = Field(description="Name of the chunk. eg README.md, module.py/func_foo", default=None)
    summary: str | None = Field(description="Summary of the node.", default=None)
    children_summaries: str | None = Field(description="Brief summary of each child node.", default=None)
    abs_path: str | None = Field(description="", default=None)
    branch: str | None = Field(description="Branch of the repo.", default=None)


class RepoNodeCreate(RepoNodeBase):
    pass


# Link on how to define composite indices in SQLModel.
# SQLModel provides abstraction for single column indices, but it appears that the
# correct way to do composite indices is to define them in db schema at the sqlalchemy level.
# https://stackoverflow.com/questions/70958639/composite-indexes-sqlmodel
class RepoNode(RepoNodeBase, MetadataMixin, table=True):
    children: list["RepoNode"] = Relationship(
        back_populates="parent",
        cascade_delete=True,
    )
    parent: Optional["RepoNode"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "reponode.c.id"},
    )

    __table_args__ = (Index('ix_org_repo', 'org', 'repo'),)


SQLModel.metadata.create_all(bind=engine)
