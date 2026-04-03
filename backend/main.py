from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from apply_runner import run_apply_job
from db import get_connection, init_db
from models import AnalyzerStatus, AnalyzerType, ApplyRequest, ApplyResult, CloneRequest, RecentProjectsResponse, ScanRequest, ScanResult
from orchestrator import is_sample_project, run_sample_project_scan, run_scan
from recent_projects import list_recent_projects
from settings import get_bool_env, get_env
from store import apply_store, store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SENSITIVE_PATH_PARTS = {
    ".aws",
    ".cursor",
    ".git",
    ".gnupg",
    ".kube",
    ".ssh",
}
SENSITIVE_PATH_PREFIXES = (
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


def _get_cors_origins() -> list[str]:
    configured = get_env("CLAUDE_OPTIMIZE_CORS_ORIGINS", default="")
    if not configured:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    if configured.strip() == "*":
        logger.warning(
            "CLAUDE_OPTIMIZE_CORS_ORIGINS is set to '*'. "
            "Any website can trigger scans on this machine."
        )
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


init_db()

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


@app.get("/api/config")
async def get_config():
    return {
        "show_github_clone": get_bool_env("CLAUDE_OPTIMIZE_SHOW_GITHUB_CLONE", default=False),
    }


_GITHUB_URL_RE = re.compile(r"^https://github\.com/[\w.\-]+/[\w.\-]+(\.git)?/?$")


@app.post("/api/clone")
async def clone_repo(request: CloneRequest):
    if not _GITHUB_URL_RE.match(request.github_url):
        raise HTTPException(
            status_code=400,
            detail="Only HTTPS GitHub URLs are supported (e.g. https://github.com/owner/repo).",
        )

    dest = Path(request.destination).expanduser().resolve()

    # Reuse the same path validation as /api/scan
    if any(part in SENSITIVE_PATH_PARTS for part in dest.parts):
        raise HTTPException(status_code=400, detail="Refusing to clone into a sensitive directory.")
    if any(_is_relative_to(dest, prefix) for prefix in SENSITIVE_PATH_PREFIXES):
        raise HTTPException(status_code=400, detail="Refusing to clone into a sensitive directory.")
    allowed_roots = _get_allowed_scan_roots()
    if not any(_is_relative_to(dest, root) for root in allowed_roots):
        allowed_text = ", ".join(str(root) for root in allowed_roots)
        raise HTTPException(
            status_code=400,
            detail=f"Clone destination must be inside an allowed root: {allowed_text}",
        )

    if dest.exists():
        if dest.is_file():
            raise HTTPException(status_code=400, detail=f"Destination path is a file, not a directory: {dest}")
        if any(dest.iterdir()):
            raise HTTPException(status_code=400, detail=f"Destination directory already exists and is not empty: {dest}")

    dest.mkdir(parents=True, exist_ok=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", request.github_url, str(dest),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(status_code=504, detail="Clone timed out after 120 seconds.")
    except FileNotFoundError:
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(status_code=500, detail="git is not installed or not found in PATH.")

    if proc.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        err_text = (stderr or stdout or b"").decode().strip()
        raise HTTPException(
            status_code=400,
            detail=f"git clone failed: {err_text}",
        )

    return {"path": str(dest)}


@app.get("/api/projects/recent", response_model=RecentProjectsResponse)
async def get_recent_projects():
    return RecentProjectsResponse(projects=list_recent_projects(limit=12))


MAX_QUEUED_SCANS = 10


@app.post("/api/scan", status_code=202)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    if store.count_active() >= MAX_QUEUED_SCANS:
        raise HTTPException(
            status_code=429,
            detail="Too many scans in progress. Please wait for existing scans to finish.",
        )

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

    if is_sample_project(project_path):
        background_tasks.add_task(run_sample_project_scan, scan_id, project_path)
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
                    if message["event"] == "stream_complete":
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "keepalive", "data": ""}
        finally:
            store.unsubscribe(scan_id, queue)

    return EventSourceResponse(event_generator())


# --- Apply endpoints ---

MAX_CONCURRENT_APPLIES = 1


@app.post("/api/apply", status_code=202)
async def start_apply(request: ApplyRequest, background_tasks: BackgroundTasks):
    if apply_store.count_active() >= MAX_CONCURRENT_APPLIES:
        raise HTTPException(
            status_code=429,
            detail="An apply job is already running. Please wait for it to finish.",
        )

    project_path = _validate_project_path(request.project_path)

    apply_id = str(uuid.uuid4())
    apply = ApplyResult(
        apply_id=apply_id,
        project_path=project_path,
        status="pending",
    )
    apply_store.create(apply)

    background_tasks.add_task(
        run_apply_job, apply_id, request.prompt, project_path,
        finding_titles=request.finding_titles,
        finding_files=request.finding_files,
        finding_docs_urls=request.finding_docs_urls,
        finding_summaries=request.finding_summaries,
        scan_id=request.scan_id or None,
    )

    return {"apply_id": apply_id, "status": "pending"}


@app.get("/api/apply/{apply_id}")
async def get_apply(apply_id: str):
    apply = apply_store.get(apply_id)
    if apply is None:
        raise HTTPException(status_code=404, detail="Apply job not found")
    return apply


@app.get("/api/apply/{apply_id}/stream")
async def apply_stream(apply_id: str):
    apply = apply_store.get(apply_id)
    if apply is None:
        raise HTTPException(status_code=404, detail="Apply job not found")

    queue = apply_store.subscribe(apply_id)

    async def event_generator():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": message["event"],
                        "data": json.dumps(message["data"]),
                    }
                    if message["event"] == "stream_complete":
                        break
                except asyncio.TimeoutError:
                    yield {"event": "keepalive", "data": ""}
        finally:
            apply_store.unsubscribe(apply_id, queue)

    return EventSourceResponse(event_generator())



@app.post("/api/apply/{apply_id}/retry-pr")
async def retry_pr(apply_id: str):
    """Re-attempt push + PR creation for a completed apply whose PR failed."""
    apply = apply_store.get(apply_id)
    if apply is None:
        raise HTTPException(status_code=404, detail="Apply job not found")
    if apply.status != "completed":
        raise HTTPException(status_code=400, detail="Apply job is not completed")
    if apply.pr_url:
        raise HTTPException(status_code=400, detail="PR already created")
    if not apply.pr_branch:
        raise HTTPException(status_code=400, detail="No branch info available for retry")

    from git_pr import retry_pull_request

    pr_title = "Claude Optimize: Apply optimizations"
    pr_body = "Optimizations applied by [Claude Optimize](https://github.com/saharmor/claude-optimize)."

    try:
        url = await retry_pull_request(
            apply.project_path, apply.pr_branch, pr_title, pr_body,
        )
        apply_store.update(apply_id, pr_url=url, pr_error=None)
        return {"pr_url": url}
    except Exception as exc:
        apply_store.update(apply_id, pr_error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# --- History endpoints ---


@app.get("/api/history/scans")
def list_scan_history(limit: int = 50, offset: int = 0):
    if limit < 0 or limit > 500:
        limit = 50
    if offset < 0:
        offset = 0
    """List past scan runs with the latest apply info inlined."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT
                s.id, s.requested_path, s.scan_mode, s.status,
                s.started_at, s.completed_at, s.duration_ms,
                s.error_text, s.no_claude_usage, s.findings_count,
                s.project_summary_json, s.scorecard_json,
                s.git_branch, s.git_head_sha,
                r.id AS repository_id, r.display_name AS repo_name, r.remote_url,
                w.id AS workspace_id,
                a.id            AS apply_id,
                a.status        AS apply_status,
                a.selection_count AS apply_selection_count,
                a.pr_url        AS apply_pr_url,
                a.pr_error      AS apply_pr_error
            FROM scan_runs s
            LEFT JOIN repositories r ON s.repository_id = r.id
            LEFT JOIN workspaces w ON s.workspace_id = w.id
            LEFT JOIN (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY source_scan_run_id ORDER BY started_at DESC
                ) AS rn
                FROM apply_jobs
                WHERE source_scan_run_id IS NOT NULL
            ) a ON a.source_scan_run_id = s.id AND a.rn = 1
            ORDER BY s.started_at DESC
            LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()

        scans = []
        for row in rows:
            scan = {
                "scan_id": row["id"],
                "project_path": row["requested_path"],
                "scan_mode": row["scan_mode"],
                "status": row["status"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "duration_ms": row["duration_ms"],
                "error": row["error_text"],
                "no_claude_usage": bool(row["no_claude_usage"]),
                "findings_count": row["findings_count"],
                "git_branch": row["git_branch"],
                "git_head_sha": row["git_head_sha"],
                "repository_id": row["repository_id"],
                "repo_name": row["repo_name"],
                "remote_url": row["remote_url"],
                "workspace_id": row["workspace_id"],
                "project_summary": None,
                "scorecard": None,
                "apply": None,
            }
            if row["project_summary_json"]:
                try:
                    scan["project_summary"] = json.loads(row["project_summary_json"])
                except Exception:
                    pass
            if row["scorecard_json"]:
                try:
                    scan["scorecard"] = json.loads(row["scorecard_json"])
                except Exception:
                    pass
            if row["apply_id"]:
                scan["apply"] = {
                    "apply_id": row["apply_id"],
                    "status": row["apply_status"],
                    "selection_count": row["apply_selection_count"],
                    "pr_url": row["apply_pr_url"],
                    "pr_error": row["apply_pr_error"],
                }
            scans.append(scan)

        total_row = conn.execute("SELECT COUNT(*) as total FROM scan_runs").fetchone()
        total = total_row["total"] if total_row else 0

        return {"scans": scans, "total": total}
    finally:
        conn.close()


@app.get("/api/history/scans/{scan_id}/analyzers")
def get_scan_analyzers(scan_id: str):
    """Get analyzer run details for a specific scan."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT analyzer_type, analyzer_group, status,
                      started_at, completed_at, duration_ms,
                      model_name, prompt_hash, result_count,
                      error_text, note_text
               FROM scan_analyzer_runs
               WHERE scan_run_id = ?
               ORDER BY analyzer_type""",
            (scan_id,),
        ).fetchall()

        analyzers = []
        for row in rows:
            analyzers.append({
                "analyzer_type": row["analyzer_type"],
                "analyzer_group": row["analyzer_group"],
                "status": row["status"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "duration_ms": row["duration_ms"],
                "model_name": row["model_name"],
                "prompt_hash": row["prompt_hash"],
                "result_count": row["result_count"],
                "error": row["error_text"],
                "note": row["note_text"],
            })

        return {"analyzers": analyzers}
    finally:
        conn.close()


@app.get("/api/history/applies")
def list_apply_history(limit: int = 50, offset: int = 0):
    if limit < 0 or limit > 500:
        limit = 50
    if offset < 0:
        offset = 0
    """List past apply jobs, most recent first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT
                a.id, a.project_path, a.status,
                a.started_at, a.completed_at, a.duration_ms,
                a.error_text, a.selection_count,
                a.pr_url, a.pr_branch, a.pr_error,
                a.source_scan_run_id,
                r.display_name AS repo_name, r.remote_url
            FROM apply_jobs a
            LEFT JOIN repositories r ON a.repository_id = r.id
            ORDER BY a.started_at DESC
            LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()

        applies = []
        for row in rows:
            applies.append({
                "apply_id": row["id"],
                "project_path": row["project_path"],
                "status": row["status"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "duration_ms": row["duration_ms"],
                "error": row["error_text"],
                "selection_count": row["selection_count"],
                "pr_url": row["pr_url"],
                "pr_branch": row["pr_branch"],
                "pr_error": row["pr_error"],
                "source_scan_run_id": row["source_scan_run_id"],
                "repo_name": row["repo_name"],
                "remote_url": row["remote_url"],
            })

        total_row = conn.execute("SELECT COUNT(*) as total FROM apply_jobs").fetchone()
        total = total_row["total"] if total_row else 0

        return {"applies": applies, "total": total}
    finally:
        conn.close()


@app.get("/api/history/applies/{apply_id}/findings")
def get_apply_findings(apply_id: str):
    """Get the findings associated with an apply job."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT ordinal, title, file_path, docs_url, summary_json, status
               FROM apply_job_findings
               WHERE apply_job_id = ?
               ORDER BY ordinal""",
            (apply_id,),
        ).fetchall()

        findings = []
        for row in rows:
            finding = {
                "ordinal": row["ordinal"],
                "title": row["title"],
                "file_path": row["file_path"],
                "docs_url": row["docs_url"],
                "status": row["status"],
                "summary": None,
            }
            if row["summary_json"]:
                try:
                    finding["summary"] = json.loads(row["summary_json"])
                except Exception:
                    pass
            findings.append(finding)

        return {"findings": findings}
    finally:
        conn.close()
