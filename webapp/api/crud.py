from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from concrete.db.orm import models, schemas

# ===Operator=== #


def create_operator(db: Session, operator: schemas.OperatorCreate) -> models.Operator:
    db_op = models.Operator(**operator.model_dump())
    db.add(db_op)
    db.commit()
    db.refresh(db_op)
    return db_op


def get_operator(db: Session, operator_id: UUID) -> models.Operator | None:
    stmt = select(models.Operator).where(models.Operator.id == operator_id)
    return db.scalars(stmt).first()


def get_operators(db: Session, skip: int = 0, limit: int = 100) -> list[models.Operator]:
    stmt = select(models.Operator).offset(skip).limit(limit)
    return db.scalars(stmt).all()


def update_operator(db: Session, operator_id: UUID, operator: schemas.OperatorUpdate) -> models.Operator | None:
    print(operator.model_dump(exclude_none=True))
    stmt = (
        update(models.Operator)
        .where(models.Operator.id == operator_id)
        .values(operator.model_dump(exclude_none=True))
        .returning(models.Operator)
    )
    ret = db.scalars(stmt).first()
    db.commit()
    return ret


def delete_operator(db: Session, operator_id: UUID) -> models.Operator | None:
    stmt = delete(models.Operator).where(models.Operator.id == operator_id).returning(models.Operator)
    ret = db.scalars(stmt).first()
    db.commit()
    return ret


# ===Client=== #


def create_client(db: Session, client: schemas.ClientCreate, operator: models.Operator) -> models.Client:
    client = models.Client(**client.model_dump() | {"operator": operator})
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_client(db: Session, client_id: UUID, operator_id: UUID) -> models.Client | None:
    stmt = select(models.Client).where(models.Client.id == client_id).where(models.Client.operator_id == operator_id)
    return db.scalars(stmt).first()


def get_clients(
    db: Session,
    operator_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[models.Client]:
    stmt = (
        (
            select(models.Client)
            if operator_id is None
            else (select(models.Client).where(models.Client.operator_id == operator_id))
        )
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def delete_client(db: Session, client_id: UUID, operator_id: UUID):
    stmt = (
        delete(models.Client)
        .where(models.Client.id == client_id)
        .where(models.Client.operator_id == operator_id)
        .returning(models.Client)
    )
    db.scalars(stmt).first()
    db.commit()


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
