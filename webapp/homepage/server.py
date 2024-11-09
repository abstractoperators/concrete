import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

dname = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(
    directory=[
        os.path.join(dname, "templates"),
    ],
)
app.mount("/static", StaticFiles(directory=os.path.join(dname, "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/pitch-deck")
async def get_pdf():
    pdf_path = "static/abstractoperators_pitchdeck.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=abstractoperators_pitchdeck.pdf"},
        )
    return {"error": "PDF not found"}


@app.get("/ping")
def ping():
    return {"message": "pong"}
