from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__

WEB = Path(__file__).parent / "web"
app = FastAPI(title="XPesquisa", version=__version__)
app.mount("/assets", StaticFiles(directory=WEB), name="assets")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
