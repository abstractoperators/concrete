from collections.abc import Sequence
from typing import TypeVar
from uuid import UUID

from sqlmodel import Session, select

from concrete.db.orm.models import (
    Base,
    Client,
    ClientCreate,
    Operator,
    OperatorCreate,
    OperatorUpdate,
)

M = TypeVar('M', bound=Base)


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
    operator = get_operator(db, operator_id)
    if operator is None:
        return None

    fields_payload = operator_update.model_dump(exclude_none=True)
    for value in fields_payload:
        setattr(operator, value, fields_payload[value])
    db.commit()
    db.refresh(operator)

    return operator


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


def delete_client(db: Session, client_id: UUID, operator_id: UUID) -> Client | None:
    return delete_generic(
        db,
        get_client(db, client_id, operator_id),
    )


# def update_operator(db: Session, operator_id: UUID, operator: schemas.OperatorUpdate) -> models.Operator | None:
#     print(operator.model_dump(exclude_none=True))
#     stmt = (
#         update(models.Operator)
#         .where(models.Operator.id == operator_id)
#         .values(operator.model_dump(exclude_none=True))
#         .returning(models.Operator)
#     )
#     ret = db.scalars(stmt).first()
#     db.commit()
#     return ret


# def delete_operator(db: Session, operator_id: UUID) -> models.Operator | None:
#     stmt = delete(models.Operator).where(models.Operator.id == operator_id).returning(models.Operator)
#     ret = db.scalars(stmt).first()
#     db.commit()
#     return ret
