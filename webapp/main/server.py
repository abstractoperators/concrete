import os
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete.db import crud
from concrete.db.orm import Session, models

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)

app = FastAPI(title="Abstract Operators: Concrete")
templates = Jinja2Templates(directory=os.path.join(dname, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chat/", response_class=HTMLResponse)
async def chat(request: Request):
    """
    Returns a list of hardcoded chat messages
    """
    messages = [
        {"Role": "Executive", "content": "I am the executive", "avatar": "E1"},
        {"Role": "Operator 1", "content": "I am operator 1", "avatar": "O1"},
        {"Role": "Operator 2", "content": "I am operator 2", "avatar": "O2"},
    ]
    return templates.TemplateResponse("group_chat.html", {"request": request, "messages": messages})


@app.get("/orchestrators", response_class=HTMLResponse)
async def get_orchestrators(request: Request):
    """
    Returns a list of all orchestrations
    """
    with Session() as session:
        orchestrators = crud.get_orchestrators(session)
    return templates.TemplateResponse("orchestrators.html", {"request": request, "orchestrators": orchestrators})


@app.get("/operators/{orchestrator_id}", response_class=HTMLResponse)
async def get_operators(request: Request, orchestrator_id: UUID):
    """
    Returns a list of all operators for a given orchestrator
    """
    with Session() as session:
        operators = crud.get_operators(session, orchestrator_id)
    return templates.TemplateResponse("operators.html", {"request": request, "operators": operators})


@app.post("/orchestrators", response_class=HTMLResponse)
async def create_orchestrator(request: Request):
    """
    Create a new orchestrator
    """
    # await json data
    orchestrator = await request.json()
    orchestrator_create = models.OrchestratorCreate(**orchestrator)

    with Session() as session:
        orchestrator = crud.create_orchestrator(session, orchestrator_create)
