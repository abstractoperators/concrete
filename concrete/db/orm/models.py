from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class Base(SQLModel):
    def __repr__(self) -> str:
        return self.model_dump_json(indent=4, exclude_unset=True, exclude_none=True)


class MetadataMixin(SQLModel):
    id: UUID = Field(primary_key=True, default_factory=uuid4)


# Operator Models


class OperatorBase(Base):
    instructions: str = Field(description="Instructions and role of the operator.")
    title: str = Field(description="Title of the operator.", max_length=32)


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


class ClientCreate(ClientBase):
    pass


class Client(ClientBase, MetadataMixin, table=True):
    operator: Operator = Relationship(back_populates="clients")


# Tool Models


class ToolBase(Base):
    pass


class Tool(ToolBase, MetadataMixin, table=True):
    operators: list[Operator] = Relationship(back_populates="tools")
