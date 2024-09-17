from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, inspect
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    def __repr__(self) -> str:
        columns = inspect(self).mapper.columns
        attrs_str = ", ".join([f"{c}={columns[c]!r}" for c in columns.keys()])
        return f"{self.__class__.__name__}({attrs_str})"


class Operator(Base):
    instructions: Mapped[str]
    title: Mapped[str] = mapped_column(String(32))

    clients: Mapped[list["Client"]] = relationship(
        back_populates="operator",
        cascade="all, delete-orphan",
    )
    tools: Mapped[list["Tool"]] = relationship(
        back_populates="operator",
        cascade="all, delete-orphan",
    )


class Client(Base):
    client: Mapped[str] = mapped_column(
        String(32), default="OpenAI"
    )  # TODO: change to more constrained type once use case is better understood
    temperature: Mapped[float] = mapped_column(default=0)
    model: Mapped[str] = mapped_column(String(32), default="gpt-4o-mini")

    operator_id: Mapped[UUID] = mapped_column(ForeignKey("operator.id"))
    operator: Mapped[Operator] = relationship(back_populates="clients")


class Tool(Base):
    operator_id: Mapped[UUID] = mapped_column(ForeignKey("operator.id"))
    operator: Mapped[Operator] = relationship(back_populates="tools")


class Node(Base):
    """
    Represents a node in a knowledge graph.
    """

    summary: Mapped[str]  # A summary of the node contents
    assoc: Mapped[str]  # What domain knowledge the node summary is associated with
    parents: Mapped[list["Node"]]  # The parent nodes of this node
    children: Mapped[list["Node"]]  # The child nodes of this node
