from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
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
        attrs_str = ", ".join([f"{c}={self.__table__.columns[c]!r}" for c in self.__table__.columns])
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
