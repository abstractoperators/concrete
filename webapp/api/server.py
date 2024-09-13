from collections.abc import Callable, Sequence
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session

from concrete.db.orm import SessionLocal
from concrete.db.orm.models import (
    Client,
    ClientCreate,
    ClientUpdate,
    Operator,
    OperatorCreate,
    OperatorUpdate,
)

from . import crud
from .models import CommonReadParameters

"""
If the db already exists and the sql models are the same, then behavior is as expected.
If the db already exists but the sql models differ, then migrations will need to be run for DB interaction
to function as expected.
"""
app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


def get_common_read_params(skip: int = 0, limit: int = 100) -> CommonReadParameters:
    return CommonReadParameters(skip=skip, limit=limit)


CommonReadDep = Annotated[CommonReadParameters, Depends(get_common_read_params)]


def object_not_found(object_name: str) -> Callable[[UUID], HTTPException]:
    def create_exception(object_uid: UUID):
        return HTTPException(status_code=404, detail=f"{object_name} {object_uid} not found")

    return create_exception


operator_not_found = object_not_found("Operator")
client_not_found = object_not_found("Client")
software_project_not_found = object_not_found("SoftwareProject")


# ===CRUD operations for Operators=== #
@app.post("/operators/", response_model=Operator)
def create_operator(operator: OperatorCreate, db: DbDep) -> Operator:
    return crud.create_operator(db, operator)


@app.get("/operators/")
def read_operators(common_read_params: CommonReadDep, db: DbDep) -> Sequence[Operator]:
    return crud.get_operators(
        db,
        common_read_params.skip,
        common_read_params.limit,
    )


@app.get("/operators/{operator_id}")
def read_operator(operator_id: UUID, db: DbDep) -> Operator:
    operator = crud.get_operator(db, operator_id)
    if operator is None:
        raise operator_not_found(operator_id)
    return operator


@app.put("/operators/{operator_id}")
def update_operator(operator_id: UUID, operator: OperatorUpdate, db: DbDep) -> Operator:
    db_op = crud.update_operator(db, operator_id, operator)
    if db_op is None:
        raise operator_not_found(operator_id)
    return db_op


@app.delete("/operators/{operator_id}")
def delete_operator(operator_id: UUID, db: DbDep) -> Operator:
    operator = crud.delete_operator(db, operator_id)
    if operator is None:
        raise operator_not_found(operator_id)
    return operator


# ===CRUD operations for Clients=== #
@app.post("/operators/{operator_id}/clients/")
def create_client(operator_id: UUID, client: ClientCreate, db: DbDep) -> Client:
    db_op = crud.get_operator(db, operator_id)
    if db_op is None:
        raise operator_not_found(operator_id)
    return crud.create_client(db, client, db_op)


@app.get("/clients/")
def read_clients(common_read_params: CommonReadDep, db: DbDep) -> Sequence[Client]:
    return crud.get_clients(
        db,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/operators/{operator_id}/clients/")
def read_operator_clients(operator_id: UUID, common_read_params: CommonReadDep, db: DbDep) -> Sequence[Client]:
    return crud.get_clients(
        db,
        operator_id=operator_id,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/operators/{operator_id}/clients/{client_id}")
def read_client(operator_id: UUID, client_id: UUID, db: DbDep) -> Client:
    client = crud.get_client(db, client_id, operator_id)
    if client is None:
        raise client_not_found(client_id)
    return client


@app.put("/operators/{operator_id}/clients/{client_id}")
def update_client(operator_id: UUID, client_id: UUID, client: ClientUpdate, db: DbDep) -> Client:
    db_client = crud.update_client(db, client_id, operator_id, client)
    if db_client is None:
        raise client_not_found(client_id)
    return db_client


@app.delete("/operators/{operator_id}/clients/{client_id}")
def delete_client(operator_id: UUID, client_id: UUID, db: DbDep) -> Client:
    client = crud.delete_client(db, client_id, operator_id)
    if client is None:
        raise client_not_found(client_id)
    return client


# # TODO
# # CRUD operations for Software Projects
# @app.post("/projects/", response_model=SoftwareProject)
# def create_project(project: SoftwareProject):
#     projects_db.append(project)
#     return project

# @app.get("/projects/", response_model=List[SoftwareProject])
# def read_projects():
#     return projects_db

# @app.get("/projects/{project_id}", response_model=SoftwareProject)
# def read_project(project_id: int):
#     for project in projects_db:
#         if project.id == project_id:
#             return project
#     raise HTTPException(status_code=404, detail="Project not found")

# @app.put("/projects/{project_id}", response_model=SoftwareProject)
# def update_project(project_id: int, updated_project: SoftwareProject):
#     for index, project in enumerate(projects_db):
#         if project.id == project_id:
#             projects_db[index] = updated_project
#             return updated_project
#     raise HTTPException(status_code=404, detail="Project not found")

# @app.delete("/projects/{project_id}")
# def delete_project(project_id: int):
#     for index, project in enumerate(projects_db):
#         if project.id == project_id:
#             del projects_db[index]
#             return
#     raise HTTPException(status_code=404, detail="Project not found")"
