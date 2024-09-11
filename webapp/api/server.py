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


def object_not_found(object_name: str) -> Callable[[UUID], HTTPException]:
    def create_exception(object_uid: UUID):
        return HTTPException(status_code=404, detail=f"{object_name} {object_uid} not found")

    return create_exception


operator_not_found = object_not_found('Operator')
client_not_found = object_not_found('Client')
software_project_not_found = object_not_found('SoftwareProject')


# CRUD operations for Operators
@app.post("/operators/", response_model=schemas.Operator)
def create_operator(operator: schemas.OperatorCreate, db: DbDep) -> models.Operator:
    return crud.create_operator(db, operator)


@app.get("/operators/", response_model=list[schemas.Operator])
def read_operators(db: DbDep, skip: int = 0, limit: int = 100) -> list[models.Operator]:
    return crud.get_operators(db, skip, limit)


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


# # CRUD operations for Clients
# @app.post("/clients/")
# def create_client(client: OpenAIClientModel) -> OpenAIClientModel:
#     clients_db.append(client)
#     return client

# @app.get("/clients/")
# def read_clients() -> list[OpenAIClientModel]:
#     return clients_db

# @app.get("/clients/{client_id}")
# def read_client(client_id: UUID) -> OpenAIClientModel:
#     for client in clients_db:
#         if client.id == client_id:
#             return client
#     raise client_not_found(client_id)

# @app.put("/clients/{client_id}")
# def update_client(client_id: UUID, updated_client: OpenAIClientModel) -> OpenAIClientModel:
#     for index, client in enumerate(clients_db):
#         if client.id == client_id:
#             clients_db[index] = updated_client
#             return updated_client
#     raise client_not_found(client_id)

# @app.delete("/clients/{client_id}")
# def delete_client(client_id: UUID):
#     for index, client in enumerate(clients_db):
#         if client.id == client_id:
#             del clients_db[index]
#             return
#     raise client_not_found(client_id)

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
