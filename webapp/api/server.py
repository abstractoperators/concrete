from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from concrete.db.orm import SessionLocal, models, schemas

from . import crud

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


def get_common_read_params(skip: int = 0, limit: int = 100) -> schemas.CommonReadParameters:
    return schemas.CommonReadParameters(skip=skip, limit=limit)


CommonReadDep = Annotated[schemas.CommonReadParameters, Depends(get_common_read_params)]


def object_not_found(object_name: str) -> Callable[[UUID], HTTPException]:
    def create_exception(object_uid: UUID):
        return HTTPException(status_code=404, detail=f"{object_name} {object_uid} not found")

    return create_exception


operator_not_found = object_not_found('Operator')
client_not_found = object_not_found('Client')
software_project_not_found = object_not_found('SoftwareProject')


# ===CRUD operations for Operators=== #
@app.post("/operators/", response_model=schemas.Operator)
def create_operator(operator: schemas.OperatorCreate, db: DbDep) -> models.Operator:
    return crud.create_operator(db, operator)


@app.get("/operators/", response_model=list[schemas.Operator])
def read_operators(common_read_params: CommonReadDep, db: DbDep) -> list[models.Operator]:
    return crud.get_operators(
        db,
        common_read_params.skip,
        common_read_params.limit,
    )


@app.get("/operators/{operator_id}", response_model=schemas.Operator)
def read_operator(operator_id: UUID, db: DbDep) -> models.Operator:
    db_op = crud.get_operator(db, operator_id)
    if db_op is None:
        raise operator_not_found(operator_id)
    return db_op


@app.put("/operators/{operator_id}", response_model=schemas.Operator)
def update_operator(operator_id: UUID, operator: schemas.OperatorUpdate, db: DbDep) -> models.Operator:
    db_op = crud.update_operator(db, operator_id, operator)
    if db_op is None:
        raise operator_not_found(operator_id)
    return db_op


@app.delete("/operators/{operator_id}")
def delete_operator(operator_id: UUID, db: DbDep):
    db_op = crud.delete_operator(db, operator_id)
    if db_op is None:
        raise operator_not_found(operator_id)
    return db_op


# ===CRUD operations for Clients=== #
@app.post("/operators/{operator_id}/clients/", response_model=schemas.Client)
def create_client(operator_id: UUID, client: schemas.ClientCreate, db: DbDep) -> models.Client:
    db_op = crud.get_operator(db, operator_id)
    if db_op is None:
        raise operator_not_found(operator_id)
    return crud.create_client(db, client, db_op)


@app.get("/clients/", response_model=list[schemas.Client])
def read_clients(common_read_params: CommonReadDep, db: DbDep) -> list[models.Client]:
    return crud.get_clients(
        db,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/operators/{operator_id}/clients/", response_model=list[schemas.Client])
def read_operator_clients(operator_id: UUID, common_read_params: CommonReadDep, db: DbDep) -> list[models.Client]:
    return crud.get_clients(
        db,
        operator_id=operator_id,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/operators/{operator_id}/clients/{client_id}", response_model=schemas.Client)
def read_client(operator_id: UUID, client_id: UUID, db: DbDep) -> models.Client:
    db_client = crud.get_client(db, client_id, operator_id)
    if db_client is None:
        raise client_not_found(client_id)
    return db_client


# # TODO
# @app.put("/clients/{client_id}")
# def update_client(client_id: UUID, updated_client: OpenAIClientModel) -> OpenAIClientModel:
#     for index, client in enumerate(clients_db):
#         if client.id == client_id:
#             clients_db[index] = updated_client
#             return updated_client
#     raise client_not_found(client_id)


# TODO
@app.delete("/operators/{operator_id}/clients/{client_id}")
def delete_client(operator_id: UUID, client_id: UUID, db: DbDep):
    db_client = crud.delete_client(db, client_id, operator_id)

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
