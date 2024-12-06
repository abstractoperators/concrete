import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Abstract Operators")

dname = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(
    directory=[
        os.path.join(dname, "templates", "components"),
        os.path.join(dname, "templates", "pages"),
    ],
)
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(name="index.html", request=request)


@app.get("/contact-us", response_class=HTMLResponse)
async def contact_us(request: Request):
    return templates.TemplateResponse(name="contact_us.html", request=request)


@app.get("/ping")
def ping():
    return {"message": "pong"}
