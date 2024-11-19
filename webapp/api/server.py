import os
from collections.abc import Callable, Sequence
from typing import Annotated
from uuid import UUID

import dotenv
from concrete.clients import CLIClient
from concrete.projects import DAGNode, Project
from concrete.webutils import AuthMiddleware
from concrete_db import crud
from concrete_db.orm.models import (
    Client,
    ClientCreate,
    ClientUpdate,
    DagNodeBase,
    DagNodeCreate,
    DagNodeToDagNodeLink,
    DagProject,
    DagProjectCreate,
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

from ..common import DbDep

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


# region Orchestrators API


@app.post("/orchestrators/", response_model=Orchestrator)
def create_orchestrator(orchestrator: OrchestratorCreate, db: DbDep) -> Orchestrator:
    return crud.create_orchestrator(db, orchestrator)


@app.get("/orchestrators/")
def get_orchestrators(common_read_params: CommonReadDep, db: DbDep) -> Sequence[Orchestrator]:
    return crud.get_orchestrators(
        db,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}")
def get_orchestrator(orchestrator_id: UUID, db: DbDep) -> Orchestrator:
    orchestrator = crud.get_orchestrator(db, orchestrator_id)
    if orchestrator is None:
        raise orchestrator_not_found(orchestrator_id)
    return orchestrator


@app.put("/orchestrators/{orchestrator_id}")
def update_orchestrator(orchestrator_id: UUID, orchestrator: OrchestratorUpdate, db: DbDep) -> Orchestrator:
    db_orc = crud.update_orchestrator(db, orchestrator_id, orchestrator)
    if db_orc is None:
        raise orchestrator_not_found(orchestrator_id)
    return db_orc


@app.delete("/orchestrators/{orchestrator_id}")
def delete_orchestrator(orchestrator_id: UUID, db: DbDep) -> Orchestrator:
    orchestrator = crud.delete_orchestrator(db, orchestrator_id)
    if orchestrator is None:
        raise orchestrator_not_found(orchestrator_id)
    return orchestrator


# endregion
# region Operators API


@app.post("/operators/")
def create_operator(operator: OperatorCreate, db: DbDep) -> Operator:
    orchestrator = crud.get_orchestrator(db, operator.orchestrator_id)
    if orchestrator is None:
        raise orchestrator_not_found(operator.orchestrator_id)
    return crud.create_operator(db, operator)


@app.get("/operators/")
def read_operators(common_read_params: CommonReadDep, db: DbDep) -> Sequence[Operator]:
    return crud.get_operators(
        db,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}/operators/")
def read_orchestrator_operators(
    orchestrator_id: UUID,
    common_read_params: CommonReadDep,
    db: DbDep,
) -> Sequence[Operator]:
    return crud.get_operators(
        db,
        orchestrator_id,
        common_read_params.skip,
        common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def read_operator(orchestrator_id: UUID, operator_id: UUID, db: DbDep) -> Operator:
    operator = crud.get_operator(db, operator_id, orchestrator_id)
    if operator is None:
        raise operator_not_found(operator_id)
    return operator


@app.put("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def update_operator(orchestrator_id: UUID, operator_id: UUID, operator: OperatorUpdate, db: DbDep) -> Operator:
    db_operator = crud.update_operator(db, operator_id, orchestrator_id, operator)
    if db_operator is None:
        raise operator_not_found(operator_id)
    return db_operator


@app.delete("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def delete_operator(orchestrator_id: UUID, operator_id: UUID, db: DbDep) -> Operator:
    operator = crud.delete_operator(db, operator_id, orchestrator_id)
    if operator is None:
        raise operator_not_found(operator_id)
    return operator


# endregion
# region Clients API


@app.post("/clients/")
def create_client(client: ClientCreate, db: DbDep) -> Client:
    operator = crud.get_operator(db, client.operator_id, client.orchestrator_id)
    if operator is None:
        raise operator_not_found(client.operator_id)
    return crud.create_client(db, client)


@app.get("/clients/")
def read_clients(common_read_params: CommonReadDep, db: DbDep) -> Sequence[Client]:
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
    db: DbDep,
) -> Sequence[Client]:
    return crud.get_clients(
        db,
        orchestrator_id=orchestrator_id,
        operator_id=operator_id,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def read_client(orchestrator_id: UUID, operator_id: UUID, client_id: UUID, db: DbDep) -> Client:
    client = crud.get_client(db, client_id, operator_id, orchestrator_id)
    if client is None:
        raise client_not_found(client_id)
    return client


@app.put("/orchestrators/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def update_client(
    orchestrator_id: UUID,
    operator_id: UUID,
    client_id: UUID,
    client: ClientUpdate,
    db: DbDep,
) -> Client:
    db_client = crud.update_client(db, client_id, operator_id, orchestrator_id, client)
    if db_client is None:
        raise client_not_found(client_id)
    return db_client


@app.delete("/orchestrators/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def delete_client(orchestrator_id: UUID, operator_id: UUID, client_id: UUID, db: DbDep) -> Client:
    client = crud.delete_client(db, client_id, operator_id, orchestrator_id)
    if client is None:
        raise client_not_found(client_id)
    return client


# endregion
# region DagProject API
# TODO: integrate better into persistence and Concept Hierarchy


@app.post("/projects/dag/")
def initialize_project(project: DagProjectCreate, db: DbDep) -> DagProject:
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
    name = project.name
    db_project = crud.get_dag_project_by_name(db, name)
    if db_project is not None:
        raise HTTPException(status_code=400, detail=f"{name} already exists as a Project!")
    db_project = crud.create_dag_project(db, project)

    return db_project


@app.get("/projects/dag/")
def read_projects(common_read_params: CommonReadDep, db: DbDep) -> Sequence[DagProject]:
    return crud.get_dag_projects(
        db,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/projects/dag/{project_name}")
def read_project(project_name: str, db: DbDep) -> DagProject:
    project = crud.get_dag_project_by_name(db, project_name)
    if project is None:
        raise project_not_found(project_name)
    return project


@app.delete("/projects/dag/{project_name}")
def delete_project(project_name: str, db: DbDep) -> DagProject:
    project = crud.delete_dag_project_by_name(db, project_name)
    if project is None:
        raise project_not_found(project_name)
    return project


@app.post("/projects/dag/{project_name}/tasks")
def expand_project_with_task(project_name: str, task: DagNodeCreate, db: DbDep) -> DagProject:
    """
    Expand a project by adding an operator task as a node in its DAG.

    project_name: The name of the project to be expanded.
    name: The name of the task instance this node represents.
    operator: The name of the operator whose task we'd like to use.
    task: The name of the operator's task to add as a node.
    default_task_kwargs: Any default arguments to pass to the task.
    options: Any options to pass to the task, e.g. tools, response format.
    """
    if project_name != task.project_name:
        raise HTTPException(
            status_code=400,
            detail=f"Path project name {project_name} and body project name {task.project_name} don't match!",
        )

    project = crud.get_dag_project_by_name(db, task.project_name)
    if project is None:
        raise project_not_found(task.project_name)

    node = crud.get_dag_node_by_name(db, project.id, task.name)
    if node is not None:
        raise HTTPException(status_code=400, detail=f"{task.name} already exists as a node for {task.project_name}!")

    crud.create_dag_node(
        db,
        DagNodeBase(
            project_id=project.id,
            **task.model_dump(exclude=set("project")),
        ),
    )

    db.refresh(project)
    return project


@app.post("/projects/dag/{project_name}/edges")
def expand_project_with_connection(project_name: str, edge: DagNodeToDagNodeLink, db: DbDep) -> DagProject:
    """
    Expand a project by connecting two tasks together.
    The output from the parent task will be fed into the child task.

    project_name: The name of the project to be expanded.
    parent_name: The name of the parent task in the connection.
    child_name: The name of the child task in the connection.
    input_to_child: The name of the input to the child (equivalently, the output from the parent)
    """
    if project_name != edge.project_name:
        raise HTTPException(
            status_code=400,
            detail=f"Path project name {project_name} and body project name {edge.project_name} don't match!",
        )

    project = crud.get_dag_project_by_name(db, edge.project_name)
    if project is None:
        raise project_not_found(edge.project_name)

    db_edge = crud.get_dag_edge(db, edge.project_name, edge.parent_name, edge.child_name)
    if db_edge is not None:
        raise HTTPException(
            status_code=400,
            detail=f"{edge.project_name} already has an edge from {edge.parent_name} to {edge.child_name}!",
        )

    crud.create_dag_edge(db, edge)

    db.refresh(project)
    return project


@app.post("/projects/dag/{project_name}/run")
async def run_project(project_name: str, db: DbDep) -> list[tuple[str, str]]:
    """
    Run a project from its sources to its sinks.

    project: The name of the project to be run.
    """
    # TODO: error handling for cycles
    db_project = crud.get_dag_project_by_name(db, project_name)
    if db_project is None:
        raise project_not_found(project_name)
    nodes = db_project.nodes
    edges = db_project.edges

    project = Project()
    for node in nodes:
        project.add_node(
            DAGNode(
                node.name,
                node.task_name,
                getattr(operators, node.operator_name)(),
                node.default_task_kwargs,
                node.options,
            )
        )
    for edge in edges:
        project.add_edge(
            edge.parent_name,
            edge.child_name,
            edge.input_to_child,
        )

    result = []
    async for operator, response in project.execute():
        CLIClient.emit(operator)
        CLIClient.emit(response.text)
        result.append((operator, response.text))

    return result


# endregion
