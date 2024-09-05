from uuid import UUID, uuid4

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Operator(DeclarativeBase):
    __table__name = "operators"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instructions: Mapped[str] = mapped_column()
    title: Mapped[str] = mapped_column()

    def __repr__(self) -> str:
        return f"Operator(id={self.id!r}, instructions={self.instructions!r}, title={self.title!r})"
