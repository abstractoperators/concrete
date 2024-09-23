from collections.abc import Sequence
from typing import TypeVar
from uuid import UUID

from sqlmodel import Session, select

from .orm.models import (
    Base,
    Client,
    ClientCreate,
    ClientUpdate,
    Message,
    MessageCreate,
    MessageUpdate,
    Node,
    NodeCreate,
    Operator,
    OperatorCreate,
    OperatorUpdate,
    Orchestrator,
    OrchestratorCreate,
    OrchestratorUpdate,
    RepoNode,
    RepoNodeCreate,
    RepoNodeUpdate,
    Tool,
    ToolCreate,
    ToolUpdate,
)

M = TypeVar("M", bound=Base)
N = TypeVar("N", bound=Base)


def create_generic(db: Session, model: M) -> M:
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


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
    return create_generic(db, Operator(**operator_create.model_dump()))


def get_operator(db: Session, operator_id: UUID, orchestrator_id: UUID) -> Operator | None:
    stmt = select(Operator).where(Operator.id == operator_id).where(Operator.orchestrator_id == orchestrator_id)
    return db.scalars(stmt).first()


def get_operators(
    db: Session,
    orchestrator_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Operator]:
    stmt = (
        (
            select(Operator)
            if orchestrator_id is None
            else select(Operator).where(Operator.orchestrator_id == orchestrator_id)
        )
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def update_operator(
    db: Session,
    operator_id: UUID,
    orchestrator_id: UUID,
    operator_update: OperatorUpdate,
) -> Operator | None:
    return update_generic(
        db,
        get_operator(db, operator_id, orchestrator_id),
        operator_update,
    )


def delete_operator(db: Session, operator_id: UUID, orchestrator_id: UUID) -> Operator | None:
    return delete_generic(
        db,
        get_operator(db, operator_id, orchestrator_id),
    )


# ===Client=== #


def create_client(db: Session, client_create: ClientCreate) -> Client:
    return create_generic(
        db,
        Client(**client_create.model_dump()),
    )


def get_client(db: Session, client_id: UUID, operator_id: UUID, orchestrator_id: UUID) -> Client | None:
    stmt = (
        select(Client)
        .where(Client.id == client_id)
        .where(Client.operator_id == operator_id)
        .where(Client.orchestrator_id == orchestrator_id)
    )
    return db.scalars(stmt).first()


def get_clients(
    db: Session,
    orchestrator_id: UUID | None = None,
    operator_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Client]:
    stmt = (
        (
            select(Client)
            if (orchestrator_id is None) or (operator_id is None)
            else (
                select(Client).where(Client.operator_id == operator_id).where(Client.orchestrator_id == orchestrator_id)
            )
        )
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def update_client(
    db: Session,
    client_id: UUID,
    operator_id: UUID,
    orchestrator_id: UUID,
    client_update: ClientUpdate,
) -> Client | None:
    return update_generic(
        db,
        get_client(db, client_id, operator_id, orchestrator_id),
        client_update,
    )


def delete_client(
    db: Session,
    client_id: UUID,
    operator_id: UUID,
    orchestrator_id: UUID,
) -> Client | None:
    return delete_generic(
        db,
        get_client(db, client_id, operator_id, orchestrator_id),
    )


# ===Tool=== #


def create_tool(db: Session, tool_create: ToolCreate) -> Tool:
    return create_generic(
        db,
        Tool(**tool_create.model_dump()),
    )


def get_tool(db: Session, tool_id: UUID) -> Tool | None:
    stmt = select(Tool).where(Tool.id == tool_id)
    return db.scalars(stmt).first()


def get_tools(
    db: Session,
    operator_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Tool]:
    stmt = (
        (select(Tool) if operator_id is None else (select(Operator.tools).where(Operator.id == operator_id)))
        .offset(skip)
        .limit(limit)
    )  # TODO: unpack from Operator.tools properly
    return db.scalars(stmt).all()


def update_tool(
    db: Session,
    tool_id: UUID,
    tool_update: ToolUpdate,
) -> Tool | None:
    return update_generic(
        db,
        get_tool(db, tool_id),
        tool_update,
    )


def delete_tool(db: Session, tool_id: UUID) -> Tool | None:
    return delete_generic(
        db,
        get_tool(db, tool_id),
    )


# ===Message=== #
def create_message(db: Session, message_create: MessageCreate) -> Message:
    return create_generic(
        db,
        Message(**message_create.model_dump()),
    )


def get_message(db: Session, message_id: UUID, orchestrator_id: UUID) -> Message | None:
    stmt = select(Message).where(Message.id == message_id).where(Message.orchestrator_id == orchestrator_id)
    return db.scalars(stmt).first()


def get_messages(
    db: Session,
    orchestrator_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Message]:
    stmt = select(Message).where(Message.orchestrator_id == orchestrator_id).offset(skip).limit(limit)
    return db.scalars(stmt).all()


def update_message(
    db: Session,
    message_id: UUID,
    orchestrator_id: UUID,
    message_update: MessageUpdate,
) -> Message | None:
    return update_generic(
        db,
        get_message(db, message_id, orchestrator_id),
        message_update,
    )


def delete_message(
    db: Session,
    message_id: UUID,
    orchestrator_id: UUID,
) -> Message | None:
    return delete_generic(db, get_message(db, message_id, orchestrator_id))


# ===Orchestrator=== #


def create_orchestrator(db: Session, orchestrator_create: OrchestratorCreate) -> Orchestrator:
    return create_generic(db, Orchestrator(**orchestrator_create.model_dump()))


def get_orchestrator(db: Session, orchestrator_id: UUID) -> Orchestrator | None:
    stmt = select(Orchestrator).where(Orchestrator.id == orchestrator_id)
    return db.scalars(stmt).first()


def get_orchestrators(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Orchestrator]:
    stmt = select(Orchestrator).offset(skip).limit(limit)
    return db.scalars(stmt).all()


def update_orchestrator(
    db: Session,
    orchestrator_id: UUID,
    orchestrator_update: OrchestratorUpdate,
) -> Orchestrator | None:
    return update_generic(
        db,
        get_orchestrator(db, orchestrator_id),
        orchestrator_update,
    )


def delete_orchestrator(db: Session, orchestrator_id: UUID) -> Orchestrator | None:
    return delete_generic(
        db,
        get_orchestrator(db, orchestrator_id),
    )


def create_node(db: Session, node_create: NodeCreate) -> Node:
    return create_generic(db, Node(**node_create.model_dump()))


def create_repo_node(db: Session, repo_node_create: RepoNodeCreate) -> RepoNode:
    return create_generic(db, RepoNode(**repo_node_create.model_dump()))


def get_repo_node(db: Session, repo_node_id: UUID) -> RepoNode | None:
    stmt = select(RepoNode).where(RepoNode.id == repo_node_id)
    return db.scalars(stmt).first()


def update_repo_node(db: Session, repo_node_id: UUID, repo_node_update: RepoNodeUpdate) -> RepoNode | None:
    return update_generic(db, get_repo_node(db, repo_node_id), repo_node_update)


def get_root_repo_node(db: Session, org: str, repo: str) -> RepoNode | None:
    # Can't do is None in sqlalchemy. Use Comparators == !=
    # or https://stackoverflow.com/questions/5602918/select-null-values-in-sqlalchemy
    stmt = select(RepoNode).where(
        RepoNode.org == org, RepoNode.repo == repo, RepoNode.parent_id.is_(None)
    )  # type: ignore # noqa
    return db.scalars(stmt).first()


def get_repo_node_by_path(db: Session, org: str, repo: str, abs_path: str) -> RepoNode | None:
    stmt = select(RepoNode).where(RepoNode.org == org, RepoNode.repo == repo, RepoNode.abs_path == abs_path)
    return db.scalars(stmt).first()
