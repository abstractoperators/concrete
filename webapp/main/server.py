import os

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
    # TODO: make dynamic, both in data and in template.
    messages = [
        {"Role": "Executive", "content": "I am the executive", "avatar": "E1"},
        {"Role": "Operator 1", "content": "I am operator 1", "avatar": "O1"},
        {"Role": "Operator 2", "content": "I am operator 2", "avatar": "O2"},
    ]
    return templates.TemplateResponse("group_chat.html", {"request": request, "messages": messages})


@app.get("/orchestrators", response_class=HTMLResponse)
async def get_orchestrators():
    with Session() as session:
        orchestrators = crud.get_orchestrators(session)
        for orchestrator in orchestrators:
            print(orchestrator)
        content = "".join(
            [
                f"""
        <li class="operator-card">
            <a href="/chat">
                <hgroup class="operator-avatar-and-header">
                    <div class="operator-avatar-container">
                        <div class="operator-avatar-mask">
                            <img src="/static/operator_circle.svg" alt="Operator Avatar" class="operator-avatar-mask">
                            <h1 class="operator-avatar-text">
                                {orchestrator.title[0] if len(orchestrator.title) < 2 else orchestrator.title[:2]}
                            </h1>
                        </div>
                    </div>

                    <h1 class="header small left">{orchestrator.title}</h1>
                </hgroup>
            </a>
        </li>
        """
                for orchestrator in orchestrators
            ]
        )
    return HTMLResponse(content=content, status_code=200)
