import os
from collections.abc import Callable, Sequence
from typing import Annotated
from uuid import UUID

import dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlmodel import Session
from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from concrete.db import crud
from concrete.db.orm import SessionLocal
from concrete.db.orm.models import (
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
from concrete.utils import verify_jwt

from .models import CommonReadParameters

dotenv.load_dotenv(override=True)

# Setup App with Middleware

middleware = [Middleware(HTTPSRedirectMiddleware)] if os.environ.get('ENV') != 'DEV' else []
middleware += [
    Middleware(
        TrustedHostMiddleware,
        allowed_hosts=[_ for _ in os.environ['HTTP_ALLOWED_HOSTS'].split(',')],
        www_redirect=False,
    ),
    Middleware(
        SessionMiddleware,
        secret_key=os.environ['HTTP_SESSION_SECRET'],
        domain=os.environ['HTTP_SESSION_DOMAIN'],
    ),
]


app = FastAPI(title="Concrete API", middleware=middleware)

# Database Setup
"""
If the db already exists and the sql models are the same, then behavior is as expected.
If the db already exists but the sql models differ, then migrations will need to be run for DB interaction
to function as expected.
"""


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


# Object Lookup Exceptions
def object_not_found(object_name: str) -> Callable[[UUID], HTTPException]:
    def create_exception(object_uid: UUID):
        return HTTPException(status_code=404, detail=f"{object_name} {object_uid} not found")

    return create_exception


orchestrator_not_found = object_not_found("Orchestrator")
operator_not_found = object_not_found("Operator")
client_not_found = object_not_found("Client")
software_project_not_found = object_not_found("SoftwareProject")
user_not_found = object_not_found("User")


def check_auth(request: Request) -> dict[str, str] | None:
    access_token = request.session.get('access_token')
    id_token = request.session.get('id_token')
    if not access_token or not id_token:
        request.session['access_token'] = None
        request.session['id_token'] = None
        return None

    try:
        payload = verify_jwt(id_token, access_token)
    except AssertionError:
        request.session['access_token'] = None
        request.session['id_token'] = None
        return None
    return payload


# ===CRUD operations for Orchestrators=== #
@app.post("/orchestrators/", response_model=Orchestrator)
def create_orchestrator(request: Request, orchestrator: OrchestratorCreate, db: DbDep) -> Orchestrator:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return crud.create_orchestrator(db, orchestrator)


@app.get("/orchestrators/")
def get_orchestrators(request: Request, common_read_params: CommonReadDep, db: DbDep) -> Sequence[Orchestrator]:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return crud.get_orchestrators(
        db,
        common_read_params.skip,
        common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}")
def get_orchestrator(request: Request, orchestrator_id: UUID, db: DbDep) -> Orchestrator:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    orchestrator = crud.get_orchestrator(db, orchestrator_id)
    if orchestrator is None:
        raise orchestrator_not_found(orchestrator_id)
    return orchestrator


@app.put("/orchestrators/{orchestrator_id}")
def update_orchestrator(
    request: Request, orchestrator_id: UUID, orchestrator: OrchestratorUpdate, db: DbDep
) -> Orchestrator:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db_orc = crud.update_orchestrator(db, orchestrator_id, orchestrator)
    if db_orc is None:
        raise orchestrator_not_found(orchestrator_id)
    return db_orc


@app.delete("/orchestrators/{orchestrator_id}")
def delete_orchestrator(request: Request, orchestrator_id: UUID, db: DbDep) -> Orchestrator:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    orchestrator = crud.delete_orchestrator(db, orchestrator_id)
    if orchestrator is None:
        raise orchestrator_not_found(orchestrator_id)
    return orchestrator


# ===CRUD operations for Operators=== #
@app.post("/operators/")
def create_operator(request: Request, operator: OperatorCreate, db: DbDep) -> Operator:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    orchestrator = crud.get_orchestrator(db, operator.orchestrator_id)
    if orchestrator is None:
        raise orchestrator_not_found(operator.orchestrator_id)
    return crud.create_operator(db, operator)


@app.get("/operators/")
def read_operators(request: Request, common_read_params: CommonReadDep, db: DbDep) -> Sequence[Operator]:
    return crud.get_operators(
        db,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}/operators/")
def read_orchestrator_operators(
    request: Request,
    orchestrator_id: UUID,
    common_read_params: CommonReadDep,
    db: DbDep,
) -> Sequence[Operator]:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return crud.get_operators(
        db,
        orchestrator_id,
        common_read_params.skip,
        common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def read_operator(request: Request, orchestrator_id: UUID, operator_id: UUID, db: DbDep) -> Operator:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    operator = crud.get_operator(db, operator_id, orchestrator_id)
    if operator is None:
        raise operator_not_found(operator_id)
    return operator


@app.put("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def update_operator(
    request: Request, orchestrator_id: UUID, operator_id: UUID, operator: OperatorUpdate, db: DbDep
) -> Operator:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db_op = crud.update_operator(db, operator_id, orchestrator_id, operator)
    if db_op is None:
        raise operator_not_found(operator_id)
    return db_op


@app.delete("/orchestrators/{orchestrator_id}/operators/{operator_id}")
def delete_operator(request: Request, orchestrator_id: UUID, operator_id: UUID, db: DbDep) -> Operator:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    operator = crud.delete_operator(db, operator_id, orchestrator_id)
    if operator is None:
        raise operator_not_found(operator_id)
    return operator


# ===CRUD operations for Clients=== #
@app.post("/clients/")
def create_client(request: Request, client: ClientCreate, db: DbDep) -> Client:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    operator = crud.get_operator(db, client.operator_id, client.orchestrator_id)
    if operator is None:
        raise operator_not_found(client.operator_id)
    return crud.create_client(db, client)


@app.get("/clients/")
def read_clients(request: Request, common_read_params: CommonReadDep, db: DbDep) -> Sequence[Client]:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return crud.get_clients(
        db,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}/clients/")
def read_operator_clients(
    request: Request, orchestrator_id: UUID, operator_id: UUID, common_read_params: CommonReadDep, db: DbDep
) -> Sequence[Client]:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return crud.get_clients(
        db,
        orchestrator_id=orchestrator_id,
        operator_id=operator_id,
        skip=common_read_params.skip,
        limit=common_read_params.limit,
    )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def read_client(request: Request, orchestrator_id: UUID, operator_id: UUID, client_id: UUID, db: DbDep) -> Client:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    client = crud.get_client(db, client_id, operator_id, orchestrator_id)
    if client is None:
        raise client_not_found(client_id)
    return client


@app.put("/orchestrator/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def update_client(
    request: Request, orchestrator_id: UUID, operator_id: UUID, client_id: UUID, client: ClientUpdate, db: DbDep
) -> Client:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db_client = crud.update_client(db, client_id, operator_id, orchestrator_id, client)
    if db_client is None:
        raise client_not_found(client_id)
    return db_client


@app.delete("/orchestrator/{orchestrator_id}/operators/{operator_id}/clients/{client_id}")
def delete_client(request: Request, orchestrator_id: UUID, operator_id: UUID, client_id: UUID, db: DbDep) -> Client:
    user_data = check_auth(request)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    client = crud.delete_client(db, client_id, operator_id, orchestrator_id)
    if client is None:
        raise client_not_found(client_id)
    return client
