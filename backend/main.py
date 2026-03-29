from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from models import AnalyzerStatus, AnalyzerType, RecentProjectsResponse, ScanRequest, ScanResult
from orchestrator import is_bundled_demo, run_demo_scan, run_scan
from recent_projects import list_recent_projects
from settings import get_env
from store import store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SENSITIVE_PATH_PARTS = {
    ".aws",
    ".cursor",
    ".git",
    ".gnupg",
    ".kube",
    ".ssh",
}
SENSITIVE_PATH_PREFIXES = tuple(
    path
    for path in (
        Path("/etc"),
        Path("/System"),
        Path("/Library"),
        Path("/private"),
        Path.home() / ".aws",
        Path.home() / ".cursor",
        Path.home() / ".gnupg",
        Path.home() / ".kube",
        Path.home() / ".ssh",
    )
    if path.exists()
)


def _get_cors_origins() -> list[str]:
    configured = get_env("CLAUDE_OPTIMIZE_CORS_ORIGINS", default="")
    if not configured:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    if configured.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def _get_allowed_scan_roots() -> list[Path]:
    configured = get_env("CLAUDE_OPTIMIZE_ALLOWED_PATHS", default="")
    if configured:
        return [
            Path(raw_root).expanduser().resolve()
            for raw_root in configured.split(",")
            if raw_root.strip()
        ]

    roots = [Path.home().resolve(), PROJECT_ROOT.resolve()]
    deduped: list[Path] = []
    for root in roots:
        if root not in deduped:
            deduped.append(root)
    return deduped


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _validate_project_path(project_path: str) -> str:
    resolved = Path(project_path).expanduser().resolve()
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {project_path}")

    if resolved == Path.home().resolve():
        raise HTTPException(
            status_code=400,
            detail="Scanning your entire home directory is not allowed. Choose a project directory instead.",
        )

    if any(part in SENSITIVE_PATH_PARTS for part in resolved.parts):
        raise HTTPException(
            status_code=400,
            detail="Refusing to scan a sensitive system or credentials directory.",
        )

    if any(_is_relative_to(resolved, prefix) for prefix in SENSITIVE_PATH_PREFIXES):
        raise HTTPException(
            status_code=400,
            detail="Refusing to scan a sensitive system or credentials directory.",
        )

    allowed_roots = _get_allowed_scan_roots()
    if not any(_is_relative_to(resolved, root) for root in allowed_roots):
        allowed_text = ", ".join(str(root) for root in allowed_roots)
        raise HTTPException(
            status_code=400,
            detail=f"Path must be inside an allowed scan root: {allowed_text}",
        )

    return str(resolved)


app = FastAPI(title="Claude Optimize", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/projects/recent", response_model=RecentProjectsResponse)
async def get_recent_projects():
    return RecentProjectsResponse(projects=list_recent_projects(limit=12))


@app.post("/api/scan", status_code=202)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    project_path = _validate_project_path(request.project_path)

    scan_id = str(uuid.uuid4())
    scan = ScanResult(
        scan_id=scan_id,
        project_path=project_path,
        status="running",
        analyzer_statuses={a: AnalyzerStatus.PENDING for a in AnalyzerType},
        started_at=datetime.now(timezone.utc),
    )
    store.create(scan)

    if is_bundled_demo(project_path):
        background_tasks.add_task(run_demo_scan, scan_id, project_path)
    else:
        background_tasks.add_task(run_scan, scan_id, project_path)

    return {"scan_id": scan_id, "status": "running"}


@app.get("/api/scan/{scan_id}")
async def get_scan(scan_id: str):
    scan = store.get(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@app.get("/api/scan/{scan_id}/stream")
async def scan_stream(scan_id: str):
    scan = store.get(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    queue = store.subscribe(scan_id)

    async def event_generator():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": message["event"],
                        "data": json.dumps(message["data"]),
                    }
                    if message["event"] == "scan_complete":
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "keepalive", "data": ""}
        finally:
            store.unsubscribe(scan_id, queue)

    return EventSourceResponse(event_generator())
