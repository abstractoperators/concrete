import asyncio
import os
import urllib
from typing import Annotated, Any
from uuid import UUID

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Form,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware import Middleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from concrete.clients import CLIClient
from concrete.db import crud
from concrete.db.orm import Session
from concrete.db.orm.models import (
    MessageCreate,
    OperatorCreate,
    OrchestratorCreate,
    ProjectCreate,
)
from concrete.models.messages import (
    ProjectDirectory,
    projectdirectory_to_zip,
    sqlmessage_to_pydanticmessage,
)
from concrete.orchestrator import SoftwareOrchestrator
from concrete.webutils import AuthMiddleware
from webapp.common import (
    ConnectionManager,
    UserIdDep,
    UserIdDepWS,
    replace_html_entities,
)

from .models import HiddenInput

load_dotenv(override=True)

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

    return templates.TemplateResponse(
        name="sidebar_create_panel.html",
        context=context,
        request=request,
    )


UNAUTHENTICATED_PATHS = {'/ping', '/login', '/docs', '/redoc', '/openapi.json', '/favicon.ico'}

# Setup App with Middleware
middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=os.environ['HTTP_SESSION_SECRET'],
        domain=os.environ['HTTP_SESSION_DOMAIN'],
    ),
    Middleware(AuthMiddleware, exclude_paths=UNAUTHENTICATED_PATHS),
]

app = FastAPI(title="Abstract Operators: Concrete", middleware=middleware)
templates = Jinja2Templates(
    directory=[
        os.path.join(dname, "templates", "pages"),
        os.path.join(dname, "templates", "components"),
    ],
)


def dyn_url_for(request: Request | WebSocket, name: str, **path_params: Any) -> str:
    url = request.url_for(name, **path_params)
    parsed = list(urllib.parse.urlparse(str(url)))
    if os.environ.get("ENV") != 'DEV':
        parsed[0] = 'https'  # Change the scheme to 'https' (Optional)
    return urllib.parse.urlunparse(parsed)


templates.env.globals['dyn_url_for'] = dyn_url_for
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")

manager = ConnectionManager()


@app.get('/login')
async def login(request: Request):
    # TODO: Replace this endpoint with html
    user_data = AuthMiddleware.check_auth(request)
    if user_data:
        return JSONResponse({"Message": "Already logged in", "email": user_data['email']})
    return JSONResponse({"login here": "https://auth.abot.ai/login"})


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(name="index.html", request=request)


@app.get("/ping")
def ping():
    return {"message": "pong"}


# === Orchestrators === #


@app.get("/orchestrators", response_class=HTMLResponse)
async def get_orchestrator_list(request: Request, user_id: UserIdDep):
    with Session() as session:
        orchestrators = crud.get_orchestrators(session, user_id)
        CLIClient.emit_sequence(orchestrators)
        CLIClient.emit("\n")
        return templates.TemplateResponse(
            name="orchestrator_list.html",
            context={"orchestrators": orchestrators},
            request=request,
        )


@app.post("/orchestrators")
async def create_orchestrator(
    title: annotatedFormStr,
    user_id: UserIdDep,
):
    # TODO: keep tabs on proper integration of Pydantic and Form. not working as expected from the FastAPI docs
    # defining parameter Annotated[OrchestratorCreate, Form()] does not extract into form data fields.
    # https://fastapi.tiangolo.com/tutorial/request-form-models/
    orchestrator_create = OrchestratorCreate(
        type_name="unknown",
        title=title,
        user_id=user_id,
    )
    with Session() as session:
        orchestrator = crud.create_orchestrator(session, orchestrator_create)
        CLIClient.emit(f"{orchestrator}\n")
        headers = {"HX-Trigger": "getOrchestrators"}
        return HTMLResponse(content=f"Created orchestrator {orchestrator.id}", headers=headers)


@app.get("/orchestrators/form", response_class=HTMLResponse)
async def create_orchestrator_form(request: Request):
    return sidebar_create(
        "Orchestrator",
        "/orchestrators",
        "orchestrator_form.html",
        request,
    )


@app.get("/orchestrators/{orchestrator_id}", response_class=HTMLResponse)
async def get_orchestrator(orchestrator_id: UUID, request: Request):
    return templates.TemplateResponse(
        name="orchestrator.html",
        context={"orchestrator_id": orchestrator_id},
        request=request,
    )


@app.delete("/orchestrators/{orchestrator_id}")
async def delete_orchestrator(orchestrator_id: UUID, user_id: UserIdDep):
    with Session() as session:
        orchestrator = crud.delete_orchestrator(session, orchestrator_id, user_id)
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
        return templates.TemplateResponse(
            name="operator_list.html",
            context={"orchestrator_id": orchestrator_id, "operators": operators},
            request=request,
        )


@app.post("/orchestrators/{orchestrator_id}/operators")
async def create_operator(
    orchestrator_id: UUID,
    title: annotatedFormStr,
    instructions: annotatedFormStr,
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
    return templates.TemplateResponse(
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
        return templates.TemplateResponse(
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
        return templates.TemplateResponse(
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
        return templates.TemplateResponse(
            name="project_chat.html",
            context={
                "chat": chat,
            },
            request=request,
        )


@app.get("/orchestrators/{orchestrator_id}/projects/{project_id}/download_finished", response_class=HTMLResponse)
async def get_downloadable_completed_project(orchestrator_id: UUID, project_id: UUID) -> StreamingResponse:

    with Session() as session:
        final_message = crud.get_completed_project(session, project_id)
        if final_message is None:
            raise HTTPException(status_code=404, detail=f"No completed project found for project {project_id}!")

        pydantic_message = sqlmessage_to_pydanticmessage(final_message)

    if not isinstance(pydantic_message, ProjectDirectory):
        raise HTTPException(
            status_code=500, detail=f"Expected ProjectDirectory, but got {pydantic_message.__class__.__name__}"
        )
    zip_buffer = projectdirectory_to_zip(pydantic_message)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=project_{project_id}.zip"},
    )


@app.websocket("/orchestrators/{orchestrator_id}/projects/{project_id}/chat/ws")
async def project_chat_ws(websocket: WebSocket, orchestrator_id: UUID, project_id: UUID, user_id: UserIdDepWS):
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
                        user_id=user_id,
                    ),
                )
                CLIClient.emit(prompt_message)
                CLIClient.emit("\n")

                project = crud.get_project(session, project_id, orchestrator_id)  # Operator pydantic type
                if project is None:
                    raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
                if project.executive_id is None or project.developer_id is None:
                    raise HTTPException(status_code=404, detail=f"Operators undefined on project {project_id}")

                sqlmodel_executive = crud.get_operator(session, (project.executive_id), orchestrator_id)
                if sqlmodel_executive is None:
                    raise HTTPException(status_code=404, detail=f"Developer {project.executive_id} not found")
                executive = sqlmodel_executive.to_obj()
                executive.project_id = project.id

                sqlmodel_developer = crud.get_operator(session, project.developer_id, orchestrator_id)
                if sqlmodel_developer is None:
                    raise HTTPException(status_code=404, detail=f"Developer {project.developer_id} not found")
                developer = sqlmodel_developer.to_obj()
                developer.project_id = project.id

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
            so = SoftwareOrchestrator()
            so.add_operator(executive, 'exec')
            so.add_operator(developer, 'dev')

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
                            <pre class="message">{ replace_html_entities(response) }</pre>
                        </li>
                    </ol>
                    """,
                    websocket,
                )
                await asyncio.sleep(0)
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
                                    {str(project.executive_id)[:2]}
                                </h1>
                            </div>
                        </div>
                        <a href="{dyn_url_for(
                            websocket,
                            'get_downloadable_completed_project',
                            orchestrator_id=orchestrator_id,
                            project_id=project_id )}">Download Files</a>
                    </li>
                </ol>
                """,
                websocket,
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
