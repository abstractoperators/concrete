from collections.abc import Sequence
from typing import TypeVar
from uuid import UUID

from sqlmodel import Session, select

from concrete.db.orm.models import (
    Base,
    Client,
    ClientCreate,
    ClientUpdate,
    Operator,
    OperatorCreate,
    OperatorUpdate,
)

M = TypeVar("M", bound=Base)
N = TypeVar("N", bound=Base)


def update_generic(db: Session, model: M | None, model_update: N) -> M | None:
    if model is None:
        return None

    fields_payload = model_update.model_dump(exclude_none=True)
    for value in fields_payload:
        setattr(model, value, fields_payload[value])
    db.commit()
    db.refresh(model)

    return model


def delete_generic(db: Session, model: M | None) -> M | None:
    if model is None:
        return None

    db.delete(model)
    db.commit()

    return model


# ===Operator=== #


def create_operator(db: Session, operator_create: OperatorCreate) -> Operator:
    operator = Operator(**operator_create.model_dump())
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator


def get_operator(db: Session, operator_id: UUID) -> Operator | None:
    stmt = select(Operator).where(Operator.id == operator_id)
    return db.scalars(stmt).first()


def get_operators(db: Session, skip: int = 0, limit: int = 100) -> Sequence[Operator]:
    stmt = select(Operator).offset(skip).limit(limit)
    return db.scalars(stmt).all()


def update_operator(db: Session, operator_id: UUID, operator_update: OperatorUpdate) -> Operator | None:
    return update_generic(
        db,
        get_operator(db, operator_id),
        operator_update,
    )


def delete_operator(db: Session, operator_id: UUID) -> Operator | None:
    return delete_generic(
        db,
        get_operator(db, operator_id),
    )


# ===Client=== #


def create_client(db: Session, client_create: ClientCreate, operator: Operator) -> Client:
    client = Client(**client_create.model_dump() | {"operator": operator})
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_client(db: Session, client_id: UUID, operator_id: UUID) -> Client | None:
    stmt = select(Client).where(Client.id == client_id).where(Client.operator_id == operator_id)
    return db.scalars(stmt).first()


def get_clients(
    db: Session,
    operator_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Client]:
    stmt = (
        (select(Client) if operator_id is None else (select(Client).where(Client.operator_id == operator_id)))
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def update_client(
    db: Session,
    client_id: UUID,
    operator_id: UUID,
    client_update: ClientUpdate,
) -> Client | None:
    return update_generic(
        db,
        get_client(db, client_id, operator_id),
        client_update,
    )


def delete_client(db: Session, client_id: UUID, operator_id: UUID) -> Client | None:
    return delete_generic(
        db,
        get_client(db, client_id, operator_id),
    )


# ===Tool=== #
def create_tool(db: Session):
    pass


def get_tool(db: Session):
    pass


def get_tools(db: Session):
    pass


def update_tool(db: Session):
    pass


def delete_tool(db: Session):
    pass
