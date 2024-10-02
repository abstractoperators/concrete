import os
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete.db import crud
from concrete.db.orm import Session
from concrete.db.orm.models import OperatorCreate, OrchestratorCreate

from .models import HiddenInput

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)

app = FastAPI(title="Abstract Operators: Concrete")
templates = Jinja2Templates(directory=os.path.join(dname, "templates"))
pages = Jinja2Templates(directory=os.path.join(dname, "templates", "pages"))
components = Jinja2Templates(directory=os.path.join(dname, "templates", "components"))
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")


annotatedFormStr = Annotated[str, Form()]


def sidebar_create(
    classname: str,
    form_endpoint: str,
    form_component: str,
    request: Request,
    hiddens: list[HiddenInput] = [],
):
    return components.TemplateResponse(
        name="sidebar_create_panel.html",
        context={
            "classname": classname,
            "form_endpoint": form_endpoint,
            "form_component": form_component,
            "hiddens": hiddens,
        },
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


@app.get("/orchestrators/sidebar/create", response_class=HTMLResponse)
async def orchestrators_sidebar_create(request: Request):
    # TODO get owner dynamically
    hiddens = [
        HiddenInput(name="owner", value="dance"),
    ]
    return sidebar_create(
        "Orchestrator",
        "/orchestrators",
        "orchestrator_form.html",
        request,
        hiddens,
    )


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
    # defining parameter Annotated[OrchestratorCreate, Form()] does not extract into form data fields.
    # https://fastapi.tiangolo.com/tutorial/request-form-models/
    operator_create = OperatorCreate(instructions=instructions, title=title, orchestrator_id=orchestrator_id)
    with Session() as session:
        crud.create_operator(session, operator_create)
        headers = {"HX-Trigger": "getOperators"}
        return HTMLResponse(content="", headers=headers)


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


@app.get("/orchestrators/{orchestrator_id}/operators/sidebar/create", response_class=HTMLResponse)
async def operators_sidebar_create(orchestrator_id: UUID, request: Request):
    return sidebar_create(
        "Operator",
        f"/orchestrators/{orchestrator_id}/operators",
        "operator_form.html",
        request,
    )
