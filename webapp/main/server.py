import asyncio
import os
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import (
    FastAPI,
    Form,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware import Middleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from concrete.clients import CLIClient
from concrete.db import crud
from concrete.db.orm import Session
from concrete.db.orm.models import (
    MessageCreate,
    OperatorCreate,
    OrchestratorCreate,
    ProjectCreate,
)
from concrete.orchestrator import SoftwareOrchestrator
from concrete.webutils import AuthMiddleware
from webapp.common import ConnectionManager

from .models import HiddenInput

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)

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


def replace_html_entities(html_text: str):
    return html_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


UNAUTHENTICATED_PATHS = {'/login', '/docs', '/redoc', '/openapi.json', '/favicon.ico'}

# Setup App with Middleware
middleware = [Middleware(HTTPSRedirectMiddleware)] if os.environ.get('ENV') != 'DEV' else []
middleware += [
    Middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.environ['HTTP_ALLOWED_HOSTS'].split(','),
        www_redirect=False,
    ),
    Middleware(
        SessionMiddleware,
        secret_key=os.environ['HTTP_SESSION_SECRET'],
        domain=os.environ['HTTP_SESSION_DOMAIN'],
    ),
    Middleware(AuthMiddleware, exclude_paths=UNAUTHENTICATED_PATHS),
]

app = FastAPI(title="Abstract Operators: Concrete", middleware=middleware)
pages = Jinja2Templates(directory=os.path.join(dname, "templates", "pages"))
components = Jinja2Templates(directory=os.path.join(dname, "templates", "components"))
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")

manager = ConnectionManager()


@app.get('/login')
async def login(request: Request):
    # TODO: Replace this endpoint with html
    user_data = AuthMiddleware.check_auth(request)
    if user_data:
        return JSONResponse({"Message": "Already logged in", "email": user_data['email']})
    return JSONResponse({"login here": "https://auth-staging.abot.ai/login"})


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return pages.TemplateResponse(name="index.html", request=request)


# === Orchestrators === #


@app.get("/orchestrators", response_class=HTMLResponse)
async def get_orchestrator_list(request: Request):
    with Session() as session:
        orchestrators = crud.get_orchestrators(session)
        CLIClient.emit_sequence(orchestrators)
        CLIClient.emit("\n")
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
        orchestrator = crud.create_orchestrator(session, orchestrator_create)
        CLIClient.emit(f"{orchestrator}\n")
        headers = {"HX-Trigger": "getOrchestrators"}
        return HTMLResponse(content=f"Created orchestrator {orchestrator.id}", headers=headers)


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
        orchestrator = crud.delete_orchestrator(session, orchestrator_id)
        CLIClient.emit(f"{orchestrator}\n")
        headers = {"HX-Trigger": "getOrchestrators"}
        return HTMLResponse(content=f"Deleted orchestrator {orchestrator_id}", headers=headers)


# === Operators === #


@app.get("/orchestrators/{orchestrator_id}/operators", response_class=HTMLResponse)
async def get_operator_list(orchestrator_id: UUID, request: Request):
    with Session() as session:
        operators = crud.get_operators(session, orchestrator_id)
        CLIClient.emit_sequence(operators)
        CLIClient.emit("\n")
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
        operator = crud.create_operator(session, operator_create)
        CLIClient.emit(f"{operator}\n")
        headers = {"HX-Trigger": "getOperators"}
        return HTMLResponse(content=f"Created operator {operator.id}", headers=headers)


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
        operator = crud.delete_operator(session, operator_id, orchestrator_id)
        CLIClient.emit(f"{operator}\n")
        headers = {"HX-Trigger": "getOperators"}
        return HTMLResponse(content=f"Deleted operator {operator_id}", headers=headers)


# === Projects === #


@app.get("/orchestrators/{orchestrator_id}/projects", response_class=HTMLResponse)
async def get_project_list(orchestrator_id: UUID, request: Request):
    with Session() as session:
        projects = crud.get_projects(session, orchestrator_id)
        CLIClient.emit_sequence(projects)
        CLIClient.emit("\n")
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
        project = crud.create_project(session, project_create)
        CLIClient.emit(f"{project}\n")
        headers = {"HX-Trigger": "getProjects"}
        return HTMLResponse(content=f"Created project {project.id}", headers=headers)


@app.get("/orchestrators/{orchestrator_id}/projects/form", response_class=HTMLResponse)
async def create_project_form(orchestrator_id: UUID, request: Request):
    with Session() as session:
        operators = crud.get_operators(session, orchestrator_id)
        CLIClient.emit_sequence(operators)
        CLIClient.emit("\n")
        return sidebar_create(
            "Project",
            f"/orchestrators/{orchestrator_id}/projects",
            "project_form.html",
            request,
            context={"operators": operators},
        )


@app.get("/orchestrators/{orchestrator_id}/projects/{project_id}", response_class=HTMLResponse)
async def get_project(orchestrator_id: UUID, project_id: UUID, request: Request):
    with Session() as session:
        project = crud.get_project(session, project_id, orchestrator_id)
        CLIClient.emit(f"{project}\n")
        return pages.TemplateResponse(
            name="project.html",
            context={
                "project": project,
            },
            request=request,
        )


@app.delete("/orchestrators/{orchestrator_id}/projects/{project_id}")
async def delete_project(orchestrator_id: UUID, project_id: UUID):
    with Session() as session:
        project = crud.delete_project(session, project_id, orchestrator_id)
        CLIClient.emit(f"{project}\n")
        headers = {"HX-Trigger": "getProjects"}
        return HTMLResponse(content=f"Deleted project {project_id}", headers=headers)


@app.get("/orchestrators/{orchestrator_id}/projects/{project_id}/chat", response_class=HTMLResponse)
async def get_project_chat(orchestrator_id: UUID, project_id: UUID, request: Request):
    with Session() as session:
        chat = crud.get_messages(session, project_id)
        CLIClient.emit_sequence(chat)
        CLIClient.emit("\n")
        return components.TemplateResponse(
            name="project_chat.html",
            context={
                "chat": chat,
            },
            request=request,
        )


@app.websocket("/orchestrators/{orchestrator_id}/projects/{project_id}/chat")
async def project_chat_ws(
    websocket: WebSocket,
    orchestrator_id: UUID,
    project_id: UUID,
):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            prompt = data["prompt"]
            with Session() as session:
                prompt_message = crud.create_message(
                    session,
                    MessageCreate(
                        type_name="text",
                        content=prompt,
                        prompt=prompt,
                        project_id=project_id,
                        user_id=uuid4(),
                        # TODO get user_id
                    ),
                )
                CLIClient.emit(prompt_message)
                CLIClient.emit("\n")

                project = crud.get_project(session, project_id, orchestrator_id)
                if project is None:
                    raise HTTPException(status_code=404, detail=f"Project {project_id} not found!")
                CLIClient.emit(project)
                CLIClient.emit("\n")

            await manager.send_text(
                f"""
                <ol id="group_chat" hx-swap-oob="beforeend">
                    <li class="right">
                        <div class="operator-avatar-container">
                            <div class="operator-avatar-mask">
                                <img
                                    src="/static/operator_circle.svg"
                                    alt="Operator Avatar"
                                    class="operator-avatar-mask"
                                >
                                <h1 class="operator-avatar-text">U</h1>
                            </div>
                        </div>
                        <p class="message">{ replace_html_entities(prompt) }</p>
                    </li>
                </ol>
                """,
                websocket,
            )
            await asyncio.sleep(0)

            CLIClient.emit(prompt)
            so = SoftwareOrchestrator(project.executive_id, project.developer_id)
            so.update(ws=websocket, manager=manager)
            async for operator, response in so.process_new_project(prompt, project.id, use_celery=False):
                CLIClient.emit(f"[{operator}]:\n{response}\n")
                is_executive = operator == "Executive"
                await manager.send_text(
                    f"""
                    <ol id="group_chat" hx-swap-oob="beforeend">
                        <li class="left">
                            <div class="operator-avatar-container">
                                <div class="operator-avatar-mask">
                                    <img
                                        src="/static/operator_circle.svg"
                                        alt="Operator Avatar"
                                        class="operator-avatar-mask"
                                    >
                                    <h1 class="operator-avatar-text">
                                        { str(project.executive_id if is_executive else project.developer_id)[:2] }
                                    </h1>
                                </div>
                            </div>
                            <p class="message">{ replace_html_entities(response) }</p>
                        </li>
                    </ol>
                    """,
                    websocket,
                )
                await asyncio.sleep(0)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
