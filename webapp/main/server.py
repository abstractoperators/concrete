import os
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from concrete.db import crud
from concrete.db.orm import Session

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
    # TODO: make dynamic in data
    messages = [
        {"Role": "Executive", "content": "I am the executive", "avatar": "E1"},
        {"Role": "Operator 1", "content": "I am operator 1", "avatar": "O1"},
        {"Role": "Operator 2", "content": "I am operator 2", "avatar": "O2"},
    ]
    return templates.TemplateResponse("group_chat.html", {"request": request, "messages": messages})


@app.get("/orchestrators", response_class=HTMLResponse)
async def get_orchestrators(request: Request):
    with Session() as session:
        orchestrators = crud.get_orchestrators(session)
    return templates.TemplateResponse("orchestrators.html", {"request": request, "orchestrators": orchestrators})


@app.get("/operators/{orchestrator_id}", response_class=HTMLResponse)
async def get_operators(request: Request, orchestrator_id: UUID):
    with Session() as session:
        operators = crud.get_operators(session, orchestrator_id)
    return templates.TemplateResponse("operators.html", {"request": request, "operators": operators})
