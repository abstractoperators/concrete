from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from concrete.db.orm import models, schemas


def get_operator(db: Session, operator_id: UUID) -> models.Operator | None:
    stmt = select(models.Operator).where(models.Operator.id == operator_id)
    return db.scalars(stmt).first()


def get_operators(db: Session, skip: int = 0, limit: int = 100) -> list[models.Operator]:
    stmt = select(models.Operator).offset(skip).limit(limit)
    return db.scalars(stmt).all()


def create_operator(db: Session, operator: schemas.OperatorCreate) -> models.Operator:
    db_op = models.Operator(**operator.model_dump())
    db.add(db_op)
    db.commit()
    db.refresh(db_op)
    return db_op


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


def create_node(db: Session, node: schemas.NodeCreate) -> models.Operator:
    db_op = models.Node(**node.model_dump())
    db.add(db_op)
    db.commit()
    db.refresh(db_op)
    return db_op
