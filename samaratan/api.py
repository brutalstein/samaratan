"""Local-first HTTP API. No user supplied command, path, or executable is accepted."""
from pathlib import Path
import shutil
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from .config import Settings
from .models import JobRequest
from .service import JobService
from .store import NotFound, Store, public_job


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = Store(settings.root)
    service = JobService(settings, store)
    app = FastAPI(title="Samaratan Studio", version="0.1.0", docs_url="/api/docs")
    app.state.store = store
    app.state.service = service

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "local-first", "engine": "godot4"}

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "providers": {"demo": True, "codex": bool(shutil.which("codex")), "claude": bool(shutil.which("claude"))},
            "engines": {"godot4": {"source_generation": True, "windows_export": bool(shutil.which(settings.godot_binary))}},
            "billing_enabled": False,
        }

    @app.post("/api/jobs", status_code=202)
    def submit(payload: JobRequest, tasks: BackgroundTasks):
        if payload.provider != "demo" and not shutil.which(payload.provider):
            raise HTTPException(status_code=422, detail=f"{payload.provider} CLI is not installed or on PATH")
        created = store.create(payload.provider, payload.prompt, payload.export_windows)
        tasks.add_task(service.run, created["id"])
        return public_job(created)

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        try:
            return public_job(store.get(job_id))
        except NotFound:
            raise HTTPException(status_code=404, detail="Job not found") from None

    @app.get("/api/jobs/{job_id}/source")
    def get_source(job_id: str):
        try:
            return FileResponse(store.output(job_id, "source_zip"), filename="samaratan-game-source.zip")
        except NotFound:
            raise HTTPException(status_code=404, detail="Source archive not available") from None

    @app.get("/api/jobs/{job_id}/windows")
    def get_windows(job_id: str):
        try:
            return FileResponse(store.output(job_id, "windows_exe"), filename="samaratan-game.exe")
        except NotFound:
            raise HTTPException(status_code=404, detail="Windows build not available") from None

    return app


app = create_app()
