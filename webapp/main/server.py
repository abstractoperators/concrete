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
from .patterns import sidebar_create

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)

app = FastAPI(title="Abstract Operators: Concrete")
templates = Jinja2Templates(directory=os.path.join(dname, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")


annotatedFormStr = Annotated[str, Form()]


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    # TODO: make dynamic, both in data and in template.
    messages = [
        {"Executive": "I am the executive!"},
        {"Operator 1": "I am operator 1!"},
        {"Operator 2": "I am operator 2!"},
        {"Operator 3": "I am operator 3!"},
    ]
    return templates.TemplateResponse("group_chat.html", {"request": request, "messages": messages})


@app.get("/orchestrators", response_class=HTMLResponse)
async def get_orchestrators():
    with Session() as session:
        orchestrators = crud.get_orchestrators(session)
        return "".join(
            [
                f"""
                <li class="operator-card">
                    <a href="/orchestrators/{o.id}">
                        <hgroup class="operator-avatar-and-header">
                            <div class="operator-avatar-container">
                                <div class="operator-avatar-mask">
                                    <img
                                        src="/static/operator_circle.svg"
                                        alt="Operator Avatar"
                                        class="operator-avatar-mask"
                                    >
                                    <h1 class="operator-avatar-text">
                                        {o.title[0] if len(o.title) < 2 else o.title[:2]}
                                    </h1>
                                </div>
                            </div>

                            <h1 class="header small left">{o.title}</h1>
                        </hgroup>
                    </a>
                    <button hx-delete="/orchestrators/{o.id}" hx-swap="none">Delete</button>
                </li>
                """
                for o in orchestrators
            ]
        )


@app.post("/orchestrators")
async def create_orchestrator(
    type_name: annotatedFormStr,
    title: annotatedFormStr,
    owner: annotatedFormStr,
):
    # TODO: keep tabs on proper integration of Pydantic and Form. not working as expected from the FastAPI docs
    orchestrator_create = OrchestratorCreate(type_name=type_name, title=title, owner=owner)
    with Session() as session:
        crud.create_orchestrator(session, orchestrator_create)
        headers = {"HX-Trigger": "getOrchestrators"}
        return HTMLResponse(content="", headers=headers)


@app.get("/orchestrators/{orchestrator_id}", response_class=HTMLResponse)
async def get_orchestrator_page(request: Request, orchestrator_id: UUID):
    return templates.TemplateResponse(
        request=request,
        name="orchestrator.html",
        context={"orchestrator_id": orchestrator_id},
    )


@app.delete("/orchestrators/{orchestrator_id}")
async def delete_orchestrator(orchestrator_id: UUID):
    with Session() as session:
        crud.delete_orchestrator(session, orchestrator_id)
        headers = {"HX-Trigger": "getOrchestrators"}
        return HTMLResponse(content="", headers=headers)


@app.get("/orchestrators/sidebar/create", response_class=HTMLResponse)
async def orchestrators_sidebar_create():
    # TODO get owner dynamically
    inputs = [
        """
        <div>
            <label for="type_name">Type</label>
            <input type="text" name="type_name" required />
        </div>
        """,
        """
        <div>
            <label for="title">Name</label>
            <input type="text" name="title" required />
        </div>
        """,
    ]
    hiddens = [
        HiddenInput(name="owner", value="dance"),
    ]
    return sidebar_create(
        "Orchestrator",
        "/orchestrators",
        inputs,
        hiddens,
    )


@app.get("/orchestrators/{orchestrator_id}/operators", response_class=HTMLResponse)
async def get_operators(orchestrator_id: UUID):
    with Session() as session:
        operators = crud.get_operators(session, orchestrator_id)
        return "".join(
            [
                f"""
                <li class="operator-card">
                    <a href="/orchestrators/{orchestrator_id}/operators/{o.id}">
                        <hgroup class="operator-avatar-and-header">
                            <div class="operator-avatar-container">
                                <div class="operator-avatar-mask">
                                    <img
                                        src="/static/operator_circle.svg"
                                        alt="Operator Avatar"
                                        class="operator-avatar-mask"
                                    >
                                    <h1 class="operator-avatar-text">
                                        {o.title[0] if len(o.title) < 2 else o.title[:2]}
                                    </h1>
                                </div>
                            </div>

                            <h1 class="header small left">{o.title}</h1>
                        </hgroup>
                    </a>
                    <button
                        hx-delete="/orchestrators/{orchestrator_id}/operators/{o.id}"
                        hx-swap="none"
                    >Delete</button>
                </li>
                """
                for o in operators
            ]
        )


@app.post("/orchestrators/{orchestrator_id}/operators")
async def create_operator(
    orchestrator_id: UUID,
    instructions: annotatedFormStr,
    title: annotatedFormStr,
):
    # TODO: keep tabs on proper integration of Pydantic and Form. not working as expected from the FastAPI docs
    operator_create = OperatorCreate(instructions=instructions, title=title, orchestrator_id=orchestrator_id)
    with Session() as session:
        crud.create_operator(session, operator_create)
        headers = {"HX-Trigger": "getOperators"}
        return HTMLResponse(content="", headers=headers)


@app.get("/orchestrators/{orchestrator_id}/operators/{operator_id}", response_class=HTMLResponse)
async def get_operator_page(request: Request, orchestrator_id: UUID, operator_id: UUID):
    return templates.TemplateResponse(
        request=request,
        name="operator.html",
        context={
            "orchestrator_id": orchestrator_id,
            "operator_id": operator_id,
        },
    )


@app.delete("/orchestrators/{orchestrator_id}/operators/{operator_id}")
async def delete_operator(orchestrator_id: UUID, operator_id: UUID):
    with Session() as session:
        crud.delete_operator(session, operator_id, orchestrator_id)
        headers = {"HX-Trigger": "getOperators"}
        return HTMLResponse(content="", headers=headers)


@app.get("/orchestrators/{orchestrator_id}/operators/sidebar/create", response_class=HTMLResponse)
async def operators_sidebar_create(orchestrator_id: UUID):
    inputs = [
        """
        <div>
            <label for="instructions">Instructions</label>
            <input type="text" name="instructions" required />
        </div>
        """,
        """
        <div>
            <label for="title">Name</label>
            <input type="text" name="title" required />
        </div>
        """,
    ]
    return sidebar_create(
        "Operator",
        f"/orchestrators/{orchestrator_id}/operators",
        inputs,
    )
