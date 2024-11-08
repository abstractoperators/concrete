import os
from collections.abc import Callable, Sequence
from typing import Annotated, Any
from uuid import UUID

import dotenv
from concrete.projects import PROJECTS, DAGNode, Project
from concrete.webutils import AuthMiddleware
from concrete_db import crud
from concrete_db.orm import Session
from concrete_db.orm.models import (
    Client,
    ClientCreate,
    ClientUpdate,
    Operator,
    OperatorCreate,
    OperatorUpdate,
    Orchestrator,
    OrchestratorCreate,
    OrchestratorUpdate,
)
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from concrete import operators

dotenv.load_dotenv(override=True)

UNAUTHENTICATED_PATHS = {"/ping", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}

# Setup App with Middleware
middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=os.environ["HTTP_SESSION_SECRET"],
        domain=os.environ["HTTP_SESSION_DOMAIN"],
    ),
    Middleware(AuthMiddleware, exclude_paths=UNAUTHENTICATED_PATHS),
]


app = FastAPI(title="Concrete API", middleware=middleware)

# Database Setup
"""
If the db already exists and the sql models are the same, then behavior is as expected.
If the db already exists but the sql models differ, then migrations will need to be run for DB interaction
to function as expected.
"""


class CommonReadParameters(BaseModel):
    skip: int
    limit: int


def get_common_read_params(skip: int = 0, limit: int = 100) -> CommonReadParameters:
    return CommonReadParameters(skip=skip, limit=limit)


CommonReadDep = Annotated[CommonReadParameters, Depends(get_common_read_params)]


# Object Lookup Exceptions
def object_not_found(object_name: str) -> Callable[[UUID | str], HTTPException]:
    def create_exception(object_uid: UUID | str):
        return HTTPException(status_code=404, detail=f"{object_name} {object_uid} not found")

    return create_exception


orchestrator_not_found = object_not_found("Orchestrator")
operator_not_found = object_not_found("Operator")
client_not_found = object_not_found("Client")
software_project_not_found = object_not_found("SoftwareProject")
project_not_found = object_not_found("Project")
user_not_found = object_not_found("User")


@app.get("/ping")
def ping():
    return {"message": "pong"}


# ===CRUD operations for Orchestrators=== #
@app.post("/orchestrators/", response_model=Orchestrator)
def create_orchestrator(orchestrator: OrchestratorCreate) -> Orchestrator:
    with Session() as db:
        return crud.create_orchestrator(db, orchestrator)


@app.get("/orchestrators/")
def get_orchestrators(common_read_params: CommonReadDep) -> Sequence[Orchestrator]:
    with Session() as db:
        return crud.get_orchestrators(
            db,
            skip=common_read_params.skip,
            limit=common_read_params.limit,
        )


@app.get("/orchestrators/{orchestrator_id}")
def get_orchestrator(orchestrator_id: UUID) -> Orchestrator:
    with Session() as db:
        orchestrator = crud.get_orchestrator(db, orchestrator_id)
        if orchestrator is None:
            raise orchestrator_not_found(orchestrator_id)
        return orchestrator


@app.put("/orchestrators/{orchestrator_id}")
def update_orchestrator(orchestrator_id: UUID, orchestrator: OrchestratorUpdate) -> Orchestrator:
    with Session() as db:
        db_orc = crud.update_orchestrator(db, orchestrator_id, orchestrator)
        if db_orc is None:
            raise orchestrator_not_found(orchestrator_id)
        return db_orc


@app.delete("/orchestrators/{orchestrator_id}")
def delete_orchestrator(orchestrator_id: UUID) -> Orchestrator:
    with Session() as db:
        orchestrator = crud.delete_orchestrator(db, orchestrator_id)
        if orchestrator is None:
            raise orchestrator_not_found(orchestrator_id)
        return orchestrator


# ===CRUD operations for Operators=== #
@app.post("/operators/")
def create_operator(operator: OperatorCreate) -> Operator:
    with Session() as db:
        orchestrator = crud.get_orchestrator(db, operator.orchestrator_id)
        if orchestrator is None:
            raise orchestrator_not_found(operator.orchestrator_id)
        return crud.create_operator(db, operator)


@app.get("/operators/")
def read_operators(common_read_params: CommonReadDep) -> Sequence[Operator]:
    with Session() as db:
        return crud.get_operators(
            db,
            skip=common_read_params.skip,
            limit=common_read_params.limit,
        )


@app.get("/orchestrators/{orchestrator_id}/operators/")
def read_orchestrator_operators(
    orchestrator_id: UUID,
    common_read_params: CommonReadDep,
) -> Sequence[Operator]:
    with Session() as db:
        return crud.get_operators(
            db,
            orchestrator_id,
            common_read_params.skip,
            common_read_params.limit,
        )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def read_operator(orchestrator_id: UUID, operator_id: UUID) -> Operator:
    with Session() as db:
        operator = crud.get_operator(db, operator_id, orchestrator_id)
        if operator is None:
            raise operator_not_found(operator_id)
        return operator


@app.put("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def update_operator(orchestrator_id: UUID, operator_id: UUID, operator: OperatorUpdate) -> Operator:
    with Session() as db:
        db_operator = crud.update_operator(db, operator_id, orchestrator_id, operator)
        if db_operator is None:
            raise operator_not_found(operator_id)
        return db_operator


@app.delete("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def delete_operator(orchestrator_id: UUID, operator_id: UUID) -> Operator:
    with Session() as db:
        operator = crud.delete_operator(db, operator_id, orchestrator_id)
        if operator is None:
            raise operator_not_found(operator_id)
        return operator


# ===CRUD operations for Clients=== #
@app.post("/clients/")
def create_client(client: ClientCreate) -> Client:
    with Session() as db:
        operator = crud.get_operator(db, client.operator_id, client.orchestrator_id)
        if operator is None:
            raise operator_not_found(client.operator_id)
        return crud.create_client(db, client)


@app.get("/clients/")
def read_clients(common_read_params: CommonReadDep) -> Sequence[Client]:
    with Session() as db:
        return crud.get_clients(
            db,
            skip=common_read_params.skip,
            limit=common_read_params.limit,
        )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}/clients/")
def read_operator_clients(
    orchestrator_id: UUID,
    operator_id: UUID,
    common_read_params: CommonReadDep,
) -> Sequence[Client]:
    with Session() as db:
        return crud.get_clients(
            db,
            orchestrator_id=orchestrator_id,
            operator_id=operator_id,
            skip=common_read_params.skip,
            limit=common_read_params.limit,
        )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def read_client(orchestrator_id: UUID, operator_id: UUID, client_id: UUID) -> Client:
    with Session() as db:
        client = crud.get_client(db, client_id, operator_id, orchestrator_id)
        if client is None:
            raise client_not_found(client_id)
        return client


@app.put("/orchestrator/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def update_client(orchestrator_id: UUID, operator_id: UUID, client_id: UUID, client: ClientUpdate) -> Client:
    with Session() as db:
        db_client = crud.update_client(db, client_id, operator_id, orchestrator_id, client)
        if db_client is None:
            raise client_not_found(client_id)
        return db_client


@app.delete("/orchestrator/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def delete_client(orchestrator_id: UUID, operator_id: UUID, client_id: UUID) -> Client:
    with Session() as db:
        client = crud.delete_client(db, client_id, operator_id, orchestrator_id)
        if client is None:
            raise client_not_found(client_id)
        return client


# ===Project and Operator Building=== #
# TODO: add persistence


@app.post("/build/project")
def initialize_project(name: str) -> str:
    """
    Initiate a directed-acyclic-graph (DAG) project locally.
    Projects must be unique in name.
    Projects are started completely empty.
    Projects contain an orchestration of operators, represented by an internal DAG.
    Projects can be expanded by adding nodes and edges
    via the endpoints for `expand_project_with_method` and `expand_project_with_connection`, respectively.
    A project node contains an operator task, while a project edge connects tasks to one another.
    Eventually, the project can be run using the endpoint for `run_project`.

    name: The name of the project to be initialized.
    """
    if name in PROJECTS:
        raise HTTPException(status_code=400, detail="{name} already exists as a Project!")
    PROJECTS[name] = Project()
    return name


@app.post("/build/project/{project}/task")
def expand_project_with_task(
    project: str, operator: str, boost: str = "chat", task: str = "", default_task_kwargs: dict[str, Any] = {}
) -> str:
    """
    Expand a project by adding an operator task as a node in its DAG.

    project: The name of the project to be expanded.
    operator: The name of the operator whose task we'd like to use.
    boost: The name of the operator's prompt boost to add as a node.
    task: The name of the task this node represents.
    default_task_kwargs: Any default arguments to pass to the task.
    """
    if project not in PROJECTS:
        raise project_not_found(project)
    project_obj = PROJECTS[project]
    node = DAGNode(task, boost, getattr(operators, operator)(), default_task_kwargs)
    return project_obj.add_node(task, node).name


@app.post("/build/project/{project}/edge")
def expand_project_with_connection(project: str, parent: str, child: str, input_to_child: str) -> tuple[str, str, str]:
    """
    Expand a project by connecting two tasks together.
    The output from the parent task will be fed into the child task.

    project: The name of the project to be expanded.
    parent: The name of the parent task in the connection.
    child: The name of the child task in the connection.
    input_to_child: The name of the input to the child (equivalently, the output from the parent)
    """
    if project not in PROJECTS:
        raise project_not_found(project)
    project_obj = PROJECTS[project]
    return project_obj.add_edge(parent, child, input_to_child)


@app.post("/build/project/{project}/run")
async def run_project(project: str):
    """
    Run a project from its sources to its sinks.

    project: The name of the project to be run.
    """
    if project not in PROJECTS:
        raise project_not_found(project)
    project_obj = PROJECTS[project]
    async for operator, response in project_obj.execute():
        print(operator)
        print(response)
