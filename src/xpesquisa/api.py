import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .connectors import EuropePMC
from .models import ResearchRequest, Run
from .pipeline import execute
from .providers import ExtractiveProvider, OllamaProvider
from .storage import Store

WEB = Path(__file__).parent / "web"


def create_app(data_dir: Path | None = None, transport=None, provider_override=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.store = Store((data_dir or Path(os.getenv("XPESQUISA_DATA_DIR", "data"))) / "xpesquisa.db")
        app.state.store.recover()
        app.state.tasks = set()
        async with httpx.AsyncClient(timeout=30, transport=transport, follow_redirects=False,
                                     headers={"User-Agent": "XPesquisa/0.2 local scientific research"}) as client:
            app.state.connector = EuropePMC(client)
            provider_name = os.getenv("XPESQUISA_PROVIDER", "extractive")
            if provider_override is not None:
                app.state.provider = provider_override
            elif provider_name == "ollama":
                app.state.provider = OllamaProvider(client, os.getenv("XPESQUISA_MODEL", ""),
                                                     os.getenv("XPESQUISA_OLLAMA_URL", "http://127.0.0.1:11434"))
            elif provider_name == "extractive":
                app.state.provider = ExtractiveProvider()
            else:
                raise ValueError("XPESQUISA_PROVIDER inválido: use extractive ou ollama.")
            yield
            tasks = list(app.state.tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="XPesquisa", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])

    @app.middleware("http")
    async def local_guard(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
            if not request.headers.get("content-type", "").startswith("application/json"):
                return JSONResponse({"detail": "Envie JSON."}, status_code=415)
            content = bytearray()
            async for chunk in request.stream():
                content.extend(chunk)
                if len(content) > 16_384:
                    return JSONResponse({"detail": "Requisição muito grande."}, status_code=413)
            request._body = bytes(content)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    app.mount("/assets", StaticFiles(directory=WEB), name="assets")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "provider": app.state.provider.name}

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    @app.get("/docs", include_in_schema=False)
    def api_docs():
        return FileResponse(WEB / "api.html")

    @app.post("/api/research", status_code=202)
    async def create_research(body: ResearchRequest):
        if len(app.state.tasks) >= 2:
            raise HTTPException(429, "Há duas pesquisas em execução. Aguarde uma delas terminar.")
        run = Run(request=body)
        app.state.store.save(run)
        task = asyncio.create_task(execute(run, app.state.store, app.state.connector, app.state.provider))
        app.state.tasks.add(task)
        task.add_done_callback(app.state.tasks.discard)
        return {"id": run.id, "status": "queued"}

    @app.get("/api/research")
    def list_research():
        return [{"id": r.id, "question": r.request.question, "status": r.status,
                 "created_at": r.created_at} for r in app.state.store.list()]

    @app.get("/api/research/{run_id}", response_model=Run)
    def get_research(run_id: UUID):
        run = app.state.store.get(str(run_id))
        if run is None:
            raise HTTPException(404, "Pesquisa não encontrada.")
        return run

    @app.get("/api/research/{run_id}/export")
    def export_research(run_id: UUID):
        run = get_research(run_id)
        body = run.model_dump(mode="json")
        for source in body["sources"]:
            source.pop("abstract", None)
        for evidence in body["evidence"]:
            evidence.pop("supporting_excerpt", None)
        for claim in body["claims"]:
            claim.pop("text", None)
        for event in body["events"]:
            event["detail"].pop("prompt", None)
        body["export_policy"] = "Metadados e vínculos; textos de fontes e afirmações omitidos. Não é um Run importável."
        return JSONResponse(body, headers={"Content-Disposition": f'attachment; filename="xpesquisa-{run.id}.json"'})

    return app


app = create_app()
