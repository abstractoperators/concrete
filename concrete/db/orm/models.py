from typing import Integer
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


# class Node(Base):
#     """
#     Table for storing nodes in a knowledge graph.
#     Each node can have one parent.
#     """

#     summary: Mapped[str] = mapped_column(String)  # A summary of the node contents
#     assoc: Mapped[str] = mapped_column(String)  # What domain knowledge the node summary is associated with

#     parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("node.id"), nullable=True)
#     parent: Mapped["Node" | None] = relationship("Node", back_populates="children", remote_side=[id])
#     children: Mapped[list["Node"] | None] = relationship("Node", back_populates="parent")


# https://docs.sqlalchemy.org/en/20/orm/self_referential.html
class Node(Base):
    summary: Mapped[str] = mapped_column(String)
    assoc: Mapped[str] = mapped_column(String)

    # Bidirectional relationship, one (parent) to many (children).
    parent_id = mapped_column(Integer, ForeignKey("node.id"))
    children = relationship("Node", back_populates="parent")
    parent = relationship("Node", back_populates="children", remote_side=[id])
