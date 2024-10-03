import os
from typing import Annotated, Any
from uuid import UUID

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete.db import crud
from concrete.db.orm import Session
from concrete.db.orm.models import OperatorCreate, OrchestratorCreate, ProjectCreate

from .models import HiddenInput

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)

app = FastAPI(title="Abstract Operators: Concrete")
templates = Jinja2Templates(directory=os.path.join(dname, "templates"))
pages = Jinja2Templates(directory=os.path.join(dname, "templates", "pages"))
components = Jinja2Templates(directory=os.path.join(dname, "templates", "components"))
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")


annotatedFormStr = Annotated[str, Form()]
annotatedFormUuid = Annotated[UUID, Form()]


def sidebar_create(
    classname: str,
    form_endpoint: str,
    form_component: str,
    request: Request,
    hiddens: list[HiddenInput] = [],
    context: dict[str, Any] = {},
):
    context |= {
        "classname": classname,
        "form_endpoint": form_endpoint,
        "form_component": form_component,
        "hiddens": hiddens,
    }

    return components.TemplateResponse(
        name="sidebar_create_panel.html",
        context=context,
        request=request,
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return pages.TemplateResponse(name="index.html", request=request)


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    # TODO: make dynamic, both in data and in template.
    messages = [
        {"Executive": "I am the executive!"},
        {"Operator 1": "I am operator 1!"},
        {"Operator 2": "I am operator 2!"},
        {"Operator 3": "I am operator 3!"},
    ]
    return templates.TemplateResponse(
        name="group_chat.html",
        context={"messages": messages},
        request=request,
    )


# === Orchestrators === #


@app.get("/orchestrators", response_class=HTMLResponse)
async def get_orchestrator_list(request: Request):
    with Session() as session:
        orchestrators = crud.get_orchestrators(session)
        return components.TemplateResponse(
            name="orchestrator_list.html",
            context={"orchestrators": orchestrators},
            request=request,
        )


@app.post("/orchestrators")
async def create_orchestrator(
    type_name: annotatedFormStr,
    title: annotatedFormStr,
    owner: annotatedFormStr,
):
    # TODO: keep tabs on proper integration of Pydantic and Form. not working as expected from the FastAPI docs
    # defining parameter Annotated[OrchestratorCreate, Form()] does not extract into form data fields.
    # https://fastapi.tiangolo.com/tutorial/request-form-models/
    orchestrator_create = OrchestratorCreate(type_name=type_name, title=title, owner=owner)
    with Session() as session:
        crud.create_orchestrator(session, orchestrator_create)
        headers = {"HX-Trigger": "getOrchestrators"}
        return HTMLResponse(content="", headers=headers)


@app.get("/orchestrators/form", response_class=HTMLResponse)
async def create_orchestrator_form(request: Request):
    # TODO get owner dynamically
    hiddens = [
        HiddenInput(name="owner", value="dance"),
    ]
    return sidebar_create(
        "Orchestrator",
        "/orchestrators",
        "orchestrator_form.html",
        request,
        hiddens=hiddens,
    )


@app.get("/orchestrators/{orchestrator_id}", response_class=HTMLResponse)
async def get_orchestrator(orchestrator_id: UUID, request: Request):
    return pages.TemplateResponse(
        name="orchestrator.html",
        context={"orchestrator_id": orchestrator_id},
        request=request,
    )


@app.delete("/orchestrators/{orchestrator_id}")
async def delete_orchestrator(orchestrator_id: UUID):
    with Session() as session:
        crud.delete_orchestrator(session, orchestrator_id)
        headers = {"HX-Trigger": "getOrchestrators"}
        return HTMLResponse(content="", headers=headers)


# === Operators === #


@app.get("/orchestrators/{orchestrator_id}/operators", response_class=HTMLResponse)
async def get_operator_list(orchestrator_id: UUID, request: Request):
    with Session() as session:
        operators = crud.get_operators(session, orchestrator_id)
        return components.TemplateResponse(
            name="operator_list.html",
            context={"orchestrator_id": orchestrator_id, "operators": operators},
            request=request,
        )


@app.post("/orchestrators/{orchestrator_id}/operators")
async def create_operator(
    orchestrator_id: UUID,
    instructions: annotatedFormStr,
    title: annotatedFormStr,
):
    # TODO: keep tabs on proper integration of Pydantic and Form. not working as expected from the FastAPI docs
    # defining parameter Annotated[OperatorCreate, Form()] does not extract into form data fields.
    # https://fastapi.tiangolo.com/tutorial/request-form-models/
    operator_create = OperatorCreate(instructions=instructions, title=title, orchestrator_id=orchestrator_id)
    with Session() as session:
        crud.create_operator(session, operator_create)
        headers = {"HX-Trigger": "getOperators"}
        return HTMLResponse(content="", headers=headers)


@app.get("/orchestrators/{orchestrator_id}/operators/form", response_class=HTMLResponse)
async def create_operator_form(orchestrator_id: UUID, request: Request):
    return sidebar_create(
        "Operator",
        f"/orchestrators/{orchestrator_id}/operators",
        "operator_form.html",
        request,
    )


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}", response_class=HTMLResponse)
async def get_operator(orchestrator_id: UUID, operator_id: UUID, request: Request):
    return pages.TemplateResponse(
        name="operator.html",
        context={
            "orchestrator_id": orchestrator_id,
            "operator_id": operator_id,
        },
        request=request,
    )


@app.delete("/orchestrators/{orchestrator_id}/operators/{operator_id}")
async def delete_operator(orchestrator_id: UUID, operator_id: UUID):
    with Session() as session:
        crud.delete_operator(session, operator_id, orchestrator_id)
        headers = {"HX-Trigger": "getOperators"}
        return HTMLResponse(content="", headers=headers)


# === Projects === #


@app.get("/orchestrators/{orchestrator_id}/projects", response_class=HTMLResponse)
async def get_project_list(orchestrator_id: UUID, request: Request):
    with Session() as session:
        projects = crud.get_projects(session, orchestrator_id)
        return components.TemplateResponse(
            name="project_list.html",
            context={"orchestrator_id": orchestrator_id, "projects": projects},
            request=request,
        )


@app.post("/orchestrators/{orchestrator_id}/projects", response_class=HTMLResponse)
async def create_project(
    orchestrator_id: UUID,
    title: annotatedFormStr,
    executive_id: annotatedFormUuid,
    developer_id: annotatedFormUuid,
):
    # TODO: keep tabs on proper integration of Pydantic and Form. not working as expected from the FastAPI docs
    # defining parameter Annotated[ProjectCreate, Form()] does not extract into form data fields.
    # https://fastapi.tiangolo.com/tutorial/request-form-models/
    project_create = ProjectCreate(
        title=title,
        executive_id=executive_id,
        developer_id=developer_id,
        orchestrator_id=orchestrator_id,
    )
    with Session() as session:
        crud.create_project(session, project_create)
        headers = {"HX-Trigger": "getProjects"}
        return HTMLResponse(content="", headers=headers)


@app.get("/orchestrators/{orchestrator_id}/projects/form", response_class=HTMLResponse)
async def create_project_form(orchestrator_id: UUID, request: Request):
    with Session() as session:
        operators = crud.get_operators(session, orchestrator_id)
        return sidebar_create(
            "Project",
            f"/orchestrators/{orchestrator_id}/projects",
            "project_form.html",
            request,
            context={"operators": operators},
        )


@app.get("/orchestrators/{orchestrator_id}/projects/{project_id}", response_class=HTMLResponse)
async def get_project(orchestrator_id: UUID, project_id: UUID, request: Request):
    return pages.TemplateResponse(
        name="project.html",
        context={
            "orchestrator_id": orchestrator_id,
            "project_id": project_id,
        },
        request=request,
    )


@app.delete("/orchestrators/{orchestrator_id}/projects/{project_id}")
async def delete_project(orchestrator_id: UUID, project_id: UUID):
    with Session() as session:
        crud.delete_project(session, project_id, orchestrator_id)
        headers = {"HX-Trigger": "getProjects"}
        return HTMLResponse(content="", headers=headers)
