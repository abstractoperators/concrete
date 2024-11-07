from collections.abc import Sequence
from typing import TypeVar
from uuid import UUID

from sqlmodel import Session, select

from .orm.models import (
    AuthState,
    AuthStateCreate,
    AuthToken,
    AuthTokenCreate,
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
    OperatorToolLink,
    OperatorUpdate,
    Orchestrator,
    OrchestratorCreate,
    OrchestratorToolLink,
    OrchestratorUpdate,
    Project,
    ProjectCreate,
    ProjectUpdate,
    RepoNode,
    RepoNodeCreate,
    RepoNodeUpdate,
    Tool,
    ToolCreate,
    User,
    UserCreate,
    UserToolLink,
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


# TODO: automate project creation via DML trigger/event
def create_operator(db: Session, operator_create: OperatorCreate) -> Operator:
    project_create = ProjectCreate(
        name=f"{operator_create.name}'s Direct Messages",
        orchestrator_id=operator_create.orchestrator_id,
    )
    project = create_project(db, project_create)

    operator = create_generic(
        db,
        Operator(
            direct_message_project_id=project.id,
            **operator_create.model_dump(),
        ),
    )

    project.direct_message_operator_id = operator.id
    db.commit()

    return operator


def get_operator(db: Session, operator_id: UUID, orchestrator_id: UUID) -> Operator | None:
    stmt = select(Operator).where(Operator.id == operator_id).where(Operator.orchestrator_id == orchestrator_id)
    res = db.scalars(stmt).first()
    if not res:
        return None
    _ = res.tools  # TODO eager load instead

    return res


def get_operator_by_name(db: Session, name: str, orchestrator_id: UUID) -> Operator | None:
    stmt = select(Operator).where(Operator.name == name).where(Operator.orchestrator_id == orchestrator_id)
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
            else select(Client)
            .where(Client.operator_id == operator_id)
            .where(Client.orchestrator_id == orchestrator_id)
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


def create_tool(db: Session, tool_create: ToolCreate, user_id: UUID) -> Tool:
    tool = create_generic(
        db,
        Tool(**tool_create.model_dump()),
    )
    assign_tool_to_user(db, user_id, tool.id)
    return tool


def get_user_tools(
    db: Session,
    user_email: str,
) -> list[Tool]:
    user = get_user(db, user_email)
    if user is None:
        return []
    return user.tools


def get_orchestrator_tools(
    db: Session,
    orchestrator_id: UUID,
    user_id: UUID,
) -> list[Tool]:
    orchestrator = get_orchestrator(db, orchestrator_id, user_id)
    if orchestrator is None:
        return []
    return orchestrator.tools


def get_operator_tools(
    db: Session,
    operator_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Tool]:
    stmt = select(Tool).where(OperatorToolLink.operator_id == operator_id).offset(skip).limit(limit)
    return db.scalars(stmt).all()


def get_tool_by_name(db: Session, user_id: UUID, tool_name: str) -> Tool | None:
    stmt = select(Tool).where(Tool.name == tool_name).where(UserToolLink.user_id == user_id)
    return db.scalars(stmt).first()


def assign_tool_to_user(db: Session, user_id: UUID, tool_id: UUID) -> UserToolLink | None:
    return create_generic(
        db,
        UserToolLink(user_id=user_id, tool_id=tool_id),
    )


def assign_tool_to_orchestrator(db: Session, orchestrator_id: UUID, tool_id: UUID) -> OrchestratorToolLink | None:
    return create_generic(
        db,
        OrchestratorToolLink(orchestrator_id=orchestrator_id, tool_id=tool_id),
    )


def assign_tool_to_operator(db: Session, operator_id: UUID, tool_id: UUID) -> OperatorToolLink | None:
    return create_generic(
        db,
        OperatorToolLink(operator_id=operator_id, tool_id=tool_id),
    )


# ===Message=== #


def create_message(db: Session, message_create: MessageCreate) -> Message:
    return create_generic(
        db,
        Message(**message_create.model_dump()),
    )


def get_message(db: Session, message_id: UUID) -> Message | None:
    stmt = select(Message).where(Message.id == message_id)
    return db.scalars(stmt).first()


def get_messages(
    db: Session,
    project_id: UUID,
    prompt: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Message]:
    stmt = (
        (select(Message) if prompt is None else select(Message).where(Message.prompt == prompt))
        .where(Message.project_id == project_id)
        .offset(skip)
        .limit(limit)
        .order_by(Message.created_at)  # type: ignore
        # TODO: need to ignore because created_at has type datetime | None; can we get it to just datetime?
    )
    return db.scalars(stmt).all()


def get_completed_project(
    db: Session,
    project_id: UUID,
    prompt: str | None = None,
) -> Message | None:
    """
    Returns message for the completed project
    # TODO Swap out for project status instead of type = projectdirectory
    """
    stmt = (
        (select(Message) if prompt is None else select(Message).where(Message.prompt == prompt))
        .where(Message.project_id == project_id)
        .where(Message.type == "ProjectDirectory")
    )
    return db.scalars(stmt).first()


def update_message(
    db: Session,
    message_id: UUID,
    message_update: MessageUpdate,
) -> Message | None:
    return update_generic(
        db,
        get_message(db, message_id),
        message_update,
    )


def delete_message(
    db: Session,
    message_id: UUID,
) -> Message | None:
    return delete_generic(db, get_message(db, message_id))


# ===Orchestrator=== #


def create_orchestrator(db: Session, orchestrator_create: OrchestratorCreate) -> Orchestrator:
    return create_generic(db, Orchestrator(**orchestrator_create.model_dump()))


def get_orchestrator(db: Session, orchestrator_id: UUID, user_id: UUID | None = None) -> Orchestrator | None:
    stmt = select(Orchestrator).where(Orchestrator.id == orchestrator_id)
    if user_id is not None:
        stmt = stmt.where(Orchestrator.user_id == user_id)
    return db.scalars(stmt).first()


def get_orchestrator_by_name(db: Session, name: str, user_id: UUID) -> Orchestrator | None:
    stmt = select(Orchestrator).where(Orchestrator.name == name).where(Orchestrator.user_id == user_id)
    return db.scalars(stmt).first()


def get_orchestrators(
    db: Session,
    user_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Orchestrator]:
    stmt = (
        (select(Orchestrator) if user_id is None else select(Orchestrator).where(Orchestrator.user_id == user_id))
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(stmt).all()


def update_orchestrator(
    db: Session,
    orchestrator_id: UUID,
    orchestrator_update: OrchestratorUpdate,
    user_id: UUID | None = None,
) -> Orchestrator | None:
    return update_generic(
        db,
        get_orchestrator(db, orchestrator_id, user_id),
        orchestrator_update,
    )


def delete_orchestrator(db: Session, orchestrator_id: UUID, user_id: UUID | None = None) -> Orchestrator | None:
    return delete_generic(
        db,
        get_orchestrator(db, orchestrator_id, user_id),
    )


# ===Project=== #


def create_project(db: Session, project_create: ProjectCreate) -> Project:
    return create_generic(db, Project(**project_create.model_dump()))


def get_project(db: Session, project_id: UUID, orchestrator_id: UUID) -> Project | None:
    stmt = select(Project).where(Project.id == project_id).where(Project.orchestrator_id == orchestrator_id)
    return db.scalars(stmt).first()


def get_project_by_name(db: Session, name: str, orchestrator_id: UUID) -> Project | None:
    stmt = select(Project).where(Project.name == name).where(Project.orchestrator_id == orchestrator_id)
    return db.scalars(stmt).first()


def get_projects(
    db: Session,
    orchestrator_id: UUID | None = None,
    include_direct_messages: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Project]:
    stmt = select(Project)
    if orchestrator_id:
        stmt = stmt.where(Project.orchestrator_id == orchestrator_id)
    if not include_direct_messages:
        stmt = stmt.where(Project.direct_message_operator_id == None)  # noqa: E711
    stmt = stmt.offset(skip).limit(limit)

    return db.scalars(stmt).all()


def update_project(
    db: Session,
    project_id: UUID,
    orchestrator_id: UUID,
    project_update: ProjectUpdate,
) -> Project | None:
    return update_generic(
        db,
        get_project(db, project_id, orchestrator_id),
        project_update,
    )


def delete_project(db: Session, project_id: UUID, orchestrator_id: UUID) -> Project | None:
    return delete_generic(
        db,
        get_project(db, project_id, orchestrator_id),
    )


# ===Node=== #
def create_node(db: Session, node_create: NodeCreate) -> Node:
    return create_generic(db, Node(**node_create.model_dump()))


def create_repo_node(db: Session, repo_node_create: RepoNodeCreate) -> RepoNode:
    return create_generic(db, RepoNode(**repo_node_create.model_dump()))


def get_repo_node(db: Session, repo_node_id: UUID) -> RepoNode | None:
    stmt = select(RepoNode).where(RepoNode.id == repo_node_id)
    return db.scalars(stmt).first()


def update_repo_node(db: Session, repo_node_id: UUID, repo_node_update: RepoNodeUpdate) -> RepoNode | None:
    return update_generic(db, get_repo_node(db, repo_node_id), repo_node_update)


def get_root_repo_node(db: Session, org: str, repo: str, branch: str = "main") -> RepoNode | None:
    # Can't do is None in sqlalchemy. Use Comparators == !=
    # or https://stackoverflow.com/questions/5602918/select-null-values-in-sqlalchemy
    stmt = select(RepoNode).where(
        RepoNode.org == org, RepoNode.repo == repo, RepoNode.parent_id.is_(None)  # type: ignore
    )
    return db.scalars(stmt).first()


def get_repo_node_by_path(db: Session, org: str, repo: str, abs_path: str, branch: str = "main") -> RepoNode | None:
    stmt = select(RepoNode).where(RepoNode.org == org, RepoNode.repo == repo, RepoNode.abs_path == abs_path)
    return db.scalars(stmt).first()


# ===User Auth=== #
def create_authstate(db: Session, authstate_create: AuthStateCreate) -> AuthState:
    return create_generic(
        db,
        AuthState(**authstate_create.model_dump()),
    )


def get_authstate(db: Session, state: str) -> AuthState | None:
    stmt = select(AuthState).where(AuthState.state == state)
    return db.scalars(stmt).first()


def create_user(db: Session, user_create: UserCreate) -> User:
    return create_generic(
        db,
        User(**user_create.model_dump()),
    )


def get_user(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return db.scalars(stmt).first()


def create_authtoken(db: Session, authtoken_create: AuthTokenCreate) -> AuthToken:
    return create_generic(db, AuthToken(**authtoken_create.model_dump()))
