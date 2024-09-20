import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# START running from make
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
# END running from make

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    messages = [
        {"Executive": "I am the executive!"},
        {"Operator 1": "I am operator 1!"},
        {"Operator 2": "I am operator 2!"},
        {"Operator 3": "I am operator 3!"},
    ]
    return templates.TemplateResponse("group_chat.html", {"request": request, "messages": messages})
