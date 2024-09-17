from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from ...state import ProjectStatus


class Base(SQLModel):
    def __repr__(self) -> str:
        return self.model_dump_json(indent=4, exclude_unset=True, exclude_none=True)


class MetadataMixin(SQLModel):
    id: UUID = Field(primary_key=True, default_factory=uuid4)


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
    tools: list["Tool"] = Relationship(back_populates="operator")
    orchestrator: "Orchestrator" = Relationship(back_populates="orchestrator")


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
    operators: list[Operator] = Relationship(back_populates="tools")


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
    orchestrator: "Orchestrator" = Relationship(back_populates="orchestrator")


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
    operators: list[Operator] = Relationship(
        back_populates="operators",
        cascade_delete=True,
    )


# TODO create user model for owner
