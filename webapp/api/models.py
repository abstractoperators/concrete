from uuid import UUID, uuid4

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instructions: Mapped[str]
    title: Mapped[str]

    def __repr__(self) -> str:
        return f"Operator(id={self.id!r}, instructions={self.instructions!r}, title={self.title!r})"
