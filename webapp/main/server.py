import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/pitch-deck")
async def get_pdf():
    pdf_path = "abstractoperators_pitchdeck.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename="abstractoperators_pitchdeck.pdf", media_type="application/pdf")
    return {"error": "PDF not found"}
