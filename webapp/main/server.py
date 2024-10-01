import os
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete.db import crud
from concrete.db.orm import Session
from concrete.db.orm.models import OrchestratorCreate

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)

app = FastAPI(title="Abstract Operators: Concrete")
templates = Jinja2Templates(directory=os.path.join(dname, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")


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
                    <a href="/chat">
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
                </li>
                """
                for o in orchestrators
            ]
        )


@app.post("/orchestrators")
async def create_orchestrator(
    type_name: Annotated[str, Form()],
    title: Annotated[str, Form()],
    owner: Annotated[str, Form()],
):
    # TODO: keep tabs on proper integration of Pydantic and Form. not working as expected from the FastAPI docs
    # async def create_orchestrator(orchestrator_create: Annotated[OrchestratorCreate, Form()]):
    orchestrator_create = OrchestratorCreate(type_name=type_name, title=title, owner=owner)
    with Session() as session:
        crud.create_orchestrator(session, orchestrator_create)
        headers = {"HX-Trigger": "newOrchestrator"}
        return HTMLResponse(content="", headers=headers)


@app.get("/orchestrators/sidebar/create", response_class=HTMLResponse)
async def orchestrators_sidebar_create():
    # TODO get owner dynamically
    return """
        <section class="sidebar right" _="on closeModal add .closing then wait for animationend then remove me">
            <h1>Create an Orchestrator</h1>
            <form hx-post="/orchestrators" hx-swap="none">
                <div>
                    <label for="type_name">Type</label>
                    <input type="text" name="type_name" required />
                </div>
                <div>
                    <label for="title">Name</label>
                    <input type="text" name="title" required />
                </div>
                <div>
                    <input
                        type="hidden"
                        name="owner"
                        value="dance"
                    />
                    <button>Create. Use SVG loader and checkmark for creation feedback.</button>
                    <button type="button" _="on click trigger closeModal">Abort</button>
                </div>
            </form>
        </section>
    """
