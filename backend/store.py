"""Hybrid in-memory + SQLite store for scan and apply state.

In-memory dicts serve live SSE streaming. SQLite provides durable persistence
so that completed scans/applies survive server restarts. On get(), the store
checks memory first and falls back to SQLite.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection
from models import (
    ANALYZER_GROUPS,
    AnalyzerStatus,
    AnalyzerType,
    ApplyResult,
    Finding,
    ProjectSummary,
    ScanResult,
    Scorecard,
)
logger = logging.getLogger(__name__)

_SAMPLE_PROJECT_PATH = (Path(__file__).resolve().parent.parent / "sample_project").resolve()

# --- Helpers for repository/workspace resolution ---

def _resolve_git_root(project_path: str) -> str | None:
    """Find the git root for a project path, or None if not a git repo."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _resolve_git_info(project_path: str) -> dict:
    """Get git branch and HEAD sha for a project path."""
    import subprocess
    info: dict = {"branch": None, "sha": None, "remote_url": None}
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_path, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            info["sha"] = result.stdout.strip()

        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_path, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            info["remote_url"] = result.stdout.strip()
    except Exception:
        pass
    return info


def ensure_repository_and_workspace(project_path: str) -> tuple[str | None, str | None, dict]:
    """Ensure a repository and workspace exist in the DB for the given path.

    Returns (repository_id, workspace_id, git_info). IDs may be None if git root
    cannot be determined (e.g. non-git directory). git_info contains branch, sha,
    and remote_url keys.
    """
    git_root = _resolve_git_root(project_path)
    git_info = _resolve_git_info(project_path) if git_root else {}
    if not git_root:
        return None, None, git_info

    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        # Upsert repository
        row = conn.execute(
            "SELECT id FROM repositories WHERE git_root = ?", (git_root,)
        ).fetchone()
        if row:
            repo_id = row["id"]
            conn.execute(
                "UPDATE repositories SET updated_at = ?, remote_url = COALESCE(?, remote_url) WHERE id = ?",
                (now, git_info.get("remote_url"), repo_id),
            )
        else:
            repo_id = str(uuid.uuid4())
            display_name = git_root.rstrip("/").rsplit("/", 1)[-1]
            conn.execute(
                """INSERT INTO repositories (id, git_root, display_name, remote_url, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (repo_id, git_root, display_name, git_info.get("remote_url"), now, now),
            )

        # Upsert workspace
        row = conn.execute(
            "SELECT id FROM workspaces WHERE canonical_path = ?", (project_path,)
        ).fetchone()
        if row:
            ws_id = row["id"]
            conn.execute(
                "UPDATE workspaces SET last_seen_at = ? WHERE id = ?", (now, ws_id),
            )
        else:
            ws_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO workspaces (id, repository_id, canonical_path, source, first_seen_at, last_seen_at)
                   VALUES (?, ?, ?, 'manual', ?, ?)""",
                (ws_id, repo_id, project_path, now, now),
            )

        conn.commit()
        return repo_id, ws_id, git_info
    except Exception:
        logger.warning("Failed to resolve repository/workspace for %s", project_path, exc_info=True)
        return None, None, git_info
    finally:
        conn.close()


# --- Analyzer group lookup ---

_ANALYZER_TO_GROUP: dict[str, str] = {}
for _group, _types in ANALYZER_GROUPS.items():
    for _at in _types:
        _ANALYZER_TO_GROUP[_at.value] = _group.value


class ScanStore:
    """Hybrid in-memory + SQLite store for scan state."""

    def __init__(self) -> None:
        self._scans: dict[str, ScanResult] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        # Track DB IDs for scan analyzer runs: (scan_id, analyzer_type) -> analyzer_run_id
        self._analyzer_run_ids: dict[tuple[str, str], str] = {}

    def create(self, scan: ScanResult) -> None:
        self._scans[scan.scan_id] = scan
        self._persist_scan_create(scan)

    def get(self, scan_id: str) -> ScanResult | None:
        # Check in-memory first (for live scans)
        scan = self._scans.get(scan_id)
        if scan is not None:
            return scan
        # Fall back to SQLite for completed scans that survived a restart
        return self._load_scan_from_db(scan_id)

    def update(self, scan_id: str, **kwargs) -> ScanResult | None:
        scan = self._scans.get(scan_id)
        if scan is None:
            return None
        for key, value in kwargs.items():
            setattr(scan, key, value)
        if scan.status in {"completed", "failed"}:
            self._persist_scan_complete(scan)
        return scan

    def add_findings(self, scan_id: str, findings: list[Finding]) -> ScanResult | None:
        scan = self._scans.get(scan_id)
        if scan is None:
            return None
        scan.findings.extend(findings)
        return scan

    def persist_findings(self, scan_id: str, findings: list[Finding], analyzer_type: AnalyzerType) -> None:
        """Persist a batch of findings to SQLite. Called after analyzer completes."""
        analyzer_run_id = self._analyzer_run_ids.get((scan_id, analyzer_type.value))
        scan = self._scans.get(scan_id)
        repo_id = None
        if scan:
            repo_id = self._get_scan_repo_id(scan_id)

        conn = get_connection()
        try:
            existing_count = conn.execute(
                "SELECT findings_count FROM scan_runs WHERE id = ?", (scan_id,)
            ).fetchone()
            offset = existing_count["findings_count"] if existing_count else 0

            for i, finding in enumerate(findings):
                finding_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO finding_instances
                       (id, scan_run_id, scan_analyzer_run_id, repository_id,
                        analyzer_type, title, model, file_path, line_range,
                        function_name, docs_url, cost_reduction, latency_reduction,
                        reliability_improvement, confidence, effort,
                        estimated_savings_detail, finding_json, sort_order)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        finding_id, scan_id, analyzer_run_id, repo_id,
                        finding.category.value, finding.recommendation.title,
                        finding.model, finding.location.file, finding.location.lines,
                        finding.location.function, finding.recommendation.docs_url,
                        finding.impact.cost_reduction, finding.impact.latency_reduction,
                        finding.impact.reliability_improvement, finding.confidence,
                        finding.effort, finding.impact.estimated_savings_detail,
                        finding.model_dump_json(), offset + i,
                    ),
                )

            # Update findings count on scan_runs
            total = offset + len(findings)
            conn.execute(
                "UPDATE scan_runs SET findings_count = ? WHERE id = ?",
                (total, scan_id),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist findings for scan %s", scan_id, exc_info=True)
        finally:
            conn.close()

    def update_analyzer_status(
        self, scan_id: str, analyzer: AnalyzerType, status: AnalyzerStatus
    ) -> None:
        scan = self._scans.get(scan_id)
        if scan:
            scan.analyzer_statuses[analyzer] = status
            self.notify(scan_id, {
                "event": "analyzer_status",
                "data": {"analyzer": analyzer.value, "status": status.value},
            })

        # Persist analyzer run to DB
        if status == AnalyzerStatus.RUNNING:
            self._persist_analyzer_run_start(scan_id, analyzer)
        elif status in {AnalyzerStatus.COMPLETED, AnalyzerStatus.FAILED}:
            self._persist_analyzer_run_end(scan_id, analyzer, status)

    def update_analyzer_error(
        self, scan_id: str, analyzer: AnalyzerType, error: str
    ) -> None:
        scan = self._scans.get(scan_id)
        if scan:
            scan.analyzer_errors[analyzer] = error
            self.notify(scan_id, {
                "event": "analyzer_failed",
                "data": {"analyzer": analyzer.value, "error": error},
            })

        # Persist error to DB
        run_id = self._analyzer_run_ids.get((scan_id, analyzer.value))
        if run_id:
            conn = get_connection()
            try:
                conn.execute(
                    "UPDATE scan_analyzer_runs SET error_text = ? WHERE id = ?",
                    (error, run_id),
                )
                conn.commit()
            except Exception:
                logger.warning("Failed to persist analyzer error", exc_info=True)
            finally:
                conn.close()

    def update_analyzer_note(self, scan_id: str, analyzer: AnalyzerType, note: str) -> None:
        """Persist a note for an analyzer run (e.g. 'Skipped: no Claude API usage')."""
        scan = self._scans.get(scan_id)
        if scan:
            scan.analyzer_notes[analyzer] = note

        run_id = self._analyzer_run_ids.get((scan_id, analyzer.value))
        if run_id:
            conn = get_connection()
            try:
                conn.execute(
                    "UPDATE scan_analyzer_runs SET note_text = ? WHERE id = ?",
                    (note, run_id),
                )
                conn.commit()
            except Exception:
                logger.warning("Failed to persist analyzer note", exc_info=True)
            finally:
                conn.close()

    def update_project_summary_status(self, scan_id: str, status: AnalyzerStatus) -> None:
        scan = self._scans.get(scan_id)
        if scan:
            scan.project_summary_status = status
            self.notify(scan_id, {
                "event": "project_summary_status",
                "data": {"status": status.value},
            })

    def set_project_summary(self, scan_id: str, summary: ProjectSummary) -> ScanResult | None:
        scan = self._scans.get(scan_id)
        if scan is None:
            return None
        scan.project_summary = summary
        scan.project_summary_error = None
        # Persist to DB
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE scan_runs SET project_summary_json = ?,
                   project_summary_status = 'completed', project_summary_error = NULL
                   WHERE id = ?""",
                (summary.model_dump_json(), scan_id),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist project summary", exc_info=True)
        finally:
            conn.close()
        return scan

    def set_project_summary_error(self, scan_id: str, error: str) -> ScanResult | None:
        scan = self._scans.get(scan_id)
        if scan is None:
            return None
        scan.project_summary_error = error
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE scan_runs SET project_summary_error = ?,
                   project_summary_status = 'failed' WHERE id = ?""",
                (error, scan_id),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist project summary error", exc_info=True)
        finally:
            conn.close()
        return scan

    def is_stream_complete(self, scan_id: str) -> bool:
        scan = self._scans.get(scan_id)
        if scan is None:
            return True
        return (
            scan.status in {"completed", "failed"}
            and scan.project_summary_status in {AnalyzerStatus.COMPLETED, AnalyzerStatus.FAILED}
        )

    def subscribe(self, scan_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(scan_id, []).append(queue)
        scan = self._scans.get(scan_id)
        if scan and self.is_stream_complete(scan_id):
            queue.put_nowait(
                {
                    "event": "stream_complete",
                    "data": {
                        "scan_id": scan_id,
                        "total_findings": len(scan.findings),
                        "status": scan.status,
                        "error": scan.error,
                    },
                }
            )
        return queue

    def unsubscribe(self, scan_id: str, queue: asyncio.Queue) -> None:
        if scan_id in self._subscribers:
            self._subscribers[scan_id] = [
                q for q in self._subscribers[scan_id] if q is not queue
            ]
            if not self._subscribers[scan_id]:
                del self._subscribers[scan_id]

    def notify(self, scan_id: str, message: dict) -> None:
        for queue in self._subscribers.get(scan_id, []):
            queue.put_nowait(message)

    def count_active(self) -> int:
        return sum(
            1 for scan in self._scans.values()
            if scan.status not in {"completed", "failed"}
        )

    # --- SQLite persistence helpers ---

    def _get_scan_repo_id(self, scan_id: str) -> str | None:
        conn = get_connection()
        try:
            row = conn.execute("SELECT repository_id FROM scan_runs WHERE id = ?", (scan_id,)).fetchone()
            return row["repository_id"] if row else None
        finally:
            conn.close()

    def _persist_scan_create(self, scan: ScanResult) -> None:
        """Write the initial scan_runs row and create scan_analyzer_runs for each analyzer."""
        repo_id, ws_id, git_info = ensure_repository_and_workspace(scan.project_path)
        now = datetime.now(timezone.utc).isoformat()

        try:
            is_demo = Path(scan.project_path).resolve() == _SAMPLE_PROJECT_PATH
        except OSError:
            is_demo = False
        scan_mode = "demo" if is_demo else "live"

        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO scan_runs
                   (id, repository_id, workspace_id, requested_path, scan_mode,
                    status, requested_at, started_at, no_claude_usage,
                    project_summary_status, git_branch, git_head_sha)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scan.scan_id, repo_id, ws_id, scan.project_path,
                    scan_mode,
                    scan.status, now, scan.started_at.isoformat() if scan.started_at else now,
                    1 if scan.no_claude_usage else 0,
                    scan.project_summary_status.value,
                    git_info.get("branch"), git_info.get("sha"),
                ),
            )

            # Create analyzer run rows for every analyzer type
            for analyzer_type in AnalyzerType:
                run_id = str(uuid.uuid4())
                group = _ANALYZER_TO_GROUP.get(analyzer_type.value, "api")
                conn.execute(
                    """INSERT INTO scan_analyzer_runs
                       (id, scan_run_id, analyzer_type, analyzer_group, status)
                       VALUES (?, ?, ?, ?, ?)""",
                    (run_id, scan.scan_id, analyzer_type.value, group, "pending"),
                )
                self._analyzer_run_ids[(scan.scan_id, analyzer_type.value)] = run_id

            conn.commit()

            # Update workspace last_scanned_at
            if ws_id:
                conn.execute(
                    "UPDATE workspaces SET last_scanned_at = ? WHERE id = ?", (now, ws_id),
                )
                conn.commit()
        except Exception:
            logger.warning("Failed to persist scan creation for %s", scan.scan_id, exc_info=True)
        finally:
            conn.close()

    def _persist_analyzer_run_start(self, scan_id: str, analyzer: AnalyzerType) -> None:
        run_id = self._analyzer_run_ids.get((scan_id, analyzer.value))
        if not run_id:
            return
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE scan_analyzer_runs SET status = 'running', started_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), run_id),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist analyzer run start", exc_info=True)
        finally:
            conn.close()

    def _persist_analyzer_run_end(self, scan_id: str, analyzer: AnalyzerType, status: AnalyzerStatus) -> None:
        run_id = self._analyzer_run_ids.get((scan_id, analyzer.value))
        if not run_id:
            return
        now = datetime.now(timezone.utc).isoformat()
        conn = get_connection()
        try:
            # Calculate duration if we have a start time
            row = conn.execute(
                "SELECT started_at FROM scan_analyzer_runs WHERE id = ?", (run_id,)
            ).fetchone()
            duration_ms = None
            if row and row["started_at"]:
                try:
                    started = datetime.fromisoformat(row["started_at"])
                    # Ensure both datetimes are timezone-aware for safe subtraction
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=timezone.utc)
                    duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
                except Exception:
                    pass

            conn.execute(
                """UPDATE scan_analyzer_runs
                   SET status = ?, completed_at = ?, duration_ms = ?
                   WHERE id = ?""",
                (status.value, now, duration_ms, run_id),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist analyzer run end", exc_info=True)
        finally:
            conn.close()

    def persist_analyzer_prompt_metadata(
        self, scan_id: str, analyzer: AnalyzerType,
        *, model_name: str | None = None, prompt_hash: str | None = None,
        prompt_version: str | None = None, raw_output: str | None = None,
        result_count: int | None = None,
    ) -> None:
        """Persist prompt metadata and raw output to the analyzer run row."""
        run_id = self._analyzer_run_ids.get((scan_id, analyzer.value))
        if not run_id:
            return
        conn = get_connection()
        try:
            sets = []
            params = []
            if model_name is not None:
                sets.append("model_name = ?")
                params.append(model_name)
            if prompt_hash is not None:
                sets.append("prompt_hash = ?")
                params.append(prompt_hash)
            if prompt_version is not None:
                sets.append("prompt_version = ?")
                params.append(prompt_version)
            if raw_output is not None:
                sets.append("raw_output_json = ?")
                params.append(raw_output)
            if result_count is not None:
                sets.append("result_count = ?")
                params.append(result_count)
            if sets:
                params.append(run_id)
                conn.execute(
                    f"UPDATE scan_analyzer_runs SET {', '.join(sets)} WHERE id = ?",
                    params,
                )
                conn.commit()
        except Exception:
            logger.warning("Failed to persist analyzer prompt metadata", exc_info=True)
        finally:
            conn.close()

    def _persist_scan_complete(self, scan: ScanResult) -> None:
        """Update the scan_runs row when scan reaches a terminal state."""
        now = datetime.now(timezone.utc).isoformat()
        duration_ms = None
        if scan.started_at and scan.completed_at:
            duration_ms = int((scan.completed_at - scan.started_at).total_seconds() * 1000)

        conn = get_connection()
        try:
            conn.execute(
                """UPDATE scan_runs
                   SET status = ?, completed_at = ?, duration_ms = ?,
                       error_text = ?, no_claude_usage = ?,
                       scorecard_json = ?, findings_count = ?,
                       project_summary_json = ?,
                       project_summary_status = ?,
                       project_summary_error = ?
                   WHERE id = ?""",
                (
                    scan.status,
                    scan.completed_at.isoformat() if scan.completed_at else now,
                    duration_ms,
                    scan.error,
                    1 if scan.no_claude_usage else 0,
                    scan.scorecard.model_dump_json() if scan.scorecard else None,
                    len(scan.findings),
                    scan.project_summary.model_dump_json() if scan.project_summary else None,
                    scan.project_summary_status.value,
                    scan.project_summary_error,
                    scan.scan_id,
                ),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist scan completion for %s", scan.scan_id, exc_info=True)
        finally:
            conn.close()

    def _load_scan_from_db(self, scan_id: str) -> ScanResult | None:
        """Reconstruct a ScanResult from SQLite for completed scans."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM scan_runs WHERE id = ?", (scan_id,)).fetchone()
            if row is None:
                return None

            # Reconstruct findings from finding_instances
            finding_rows = conn.execute(
                "SELECT finding_json FROM finding_instances WHERE scan_run_id = ? ORDER BY sort_order",
                (scan_id,),
            ).fetchall()
            findings = []
            for fr in finding_rows:
                try:
                    findings.append(Finding.model_validate_json(fr["finding_json"]))
                except Exception:
                    logger.warning("Failed to deserialize finding for scan %s", scan_id)

            # Reconstruct analyzer statuses from scan_analyzer_runs
            analyzer_rows = conn.execute(
                "SELECT analyzer_type, status, error_text, note_text FROM scan_analyzer_runs WHERE scan_run_id = ?",
                (scan_id,),
            ).fetchall()
            analyzer_statuses: dict[AnalyzerType, AnalyzerStatus] = {}
            analyzer_errors: dict[AnalyzerType, str] = {}
            analyzer_notes: dict[AnalyzerType, str] = {}
            for ar in analyzer_rows:
                try:
                    at = AnalyzerType(ar["analyzer_type"])
                    analyzer_statuses[at] = AnalyzerStatus(ar["status"])
                    if ar["error_text"]:
                        analyzer_errors[at] = ar["error_text"]
                    if ar["note_text"]:
                        analyzer_notes[at] = ar["note_text"]
                except Exception:
                    pass

            # Reconstruct project summary
            project_summary = None
            if row["project_summary_json"]:
                try:
                    project_summary = ProjectSummary.model_validate_json(row["project_summary_json"])
                except Exception:
                    pass

            # Reconstruct scorecard
            scorecard = None
            if row["scorecard_json"]:
                try:
                    scorecard = Scorecard.model_validate_json(row["scorecard_json"])
                except Exception:
                    pass

            scan = ScanResult(
                scan_id=scan_id,
                project_path=row["requested_path"],
                status=row["status"],
                analyzer_statuses=analyzer_statuses,
                analyzer_errors=analyzer_errors,
                analyzer_notes=analyzer_notes,
                findings=findings,
                scorecard=scorecard,
                project_summary=project_summary,
                project_summary_status=AnalyzerStatus(row["project_summary_status"]) if row["project_summary_status"] else AnalyzerStatus.PENDING,
                project_summary_error=row["project_summary_error"],
                no_claude_usage=bool(row["no_claude_usage"]),
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                error=row["error_text"],
            )

            # Cache in memory for subsequent requests
            self._scans[scan_id] = scan
            return scan

        except Exception:
            logger.warning("Failed to load scan %s from database", scan_id, exc_info=True)
            return None
        finally:
            conn.close()


class ApplyStore:
    """Hybrid in-memory + SQLite store for apply jobs."""

    def __init__(self) -> None:
        self._applies: dict[str, ApplyResult] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def create(self, apply: ApplyResult) -> None:
        self._applies[apply.apply_id] = apply
        self._persist_apply_create(apply)

    def get(self, apply_id: str) -> ApplyResult | None:
        apply = self._applies.get(apply_id)
        if apply is not None:
            return apply
        return self._load_apply_from_db(apply_id)

    def update(self, apply_id: str, **kwargs) -> ApplyResult | None:
        apply = self._applies.get(apply_id)
        if apply is None:
            return None
        for key, value in kwargs.items():
            setattr(apply, key, value)
        if apply.status in {"completed", "failed"}:
            self._persist_apply_complete(apply)
        else:
            # Persist intermediate updates (e.g. pr_branch, pr_url)
            self._persist_apply_update(apply)
        return apply

    def subscribe(self, apply_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(apply_id, []).append(queue)
        apply = self._applies.get(apply_id)
        if apply and apply.status in {"completed", "failed"}:
            queue.put_nowait({
                "event": "stream_complete",
                "data": {
                    "apply_id": apply_id,
                    "status": apply.status,
                    "error": apply.error,
                },
            })
        return queue

    def unsubscribe(self, apply_id: str, queue: asyncio.Queue) -> None:
        if apply_id in self._subscribers:
            self._subscribers[apply_id] = [
                q for q in self._subscribers[apply_id] if q is not queue
            ]
            if not self._subscribers[apply_id]:
                del self._subscribers[apply_id]

    def notify(self, apply_id: str, message: dict) -> None:
        for queue in self._subscribers.get(apply_id, []):
            queue.put_nowait(message)

    def count_active(self) -> int:
        return sum(
            1 for apply in self._applies.values()
            if apply.status not in {"completed", "failed"}
        )

    # --- SQLite persistence helpers ---

    def persist_apply_metadata(
        self, apply_id: str, *,
        prompt_text: str | None = None,
        selection_count: int | None = None,
        source_scan_run_id: str | None = None,
    ) -> None:
        """Persist prompt text, selection count, and source scan on the apply_jobs row."""
        conn = get_connection()
        try:
            sets = []
            params: list = []
            if prompt_text is not None:
                sets.append("prompt_text = ?")
                params.append(prompt_text)
            if selection_count is not None:
                sets.append("selection_count = ?")
                params.append(selection_count)
            if source_scan_run_id is not None:
                sets.append("source_scan_run_id = ?")
                params.append(source_scan_run_id)
            if sets:
                params.append(apply_id)
                conn.execute(
                    f"UPDATE apply_jobs SET {', '.join(sets)} WHERE id = ?",
                    params,
                )
                conn.commit()
        except Exception:
            logger.warning("Failed to persist apply metadata for %s", apply_id, exc_info=True)
        finally:
            conn.close()

    def persist_apply_job_findings(
        self, apply_id: str,
        titles: list[str], files: list[str],
        docs_urls: list[str], summaries_json: list[str],
    ) -> None:
        """Write apply_job_findings rows for each selected finding."""
        conn = get_connection()
        try:
            for i in range(len(titles)):
                finding_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO apply_job_findings
                       (id, apply_job_id, ordinal, title, file_path, docs_url, summary_json, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                    (
                        finding_id, apply_id, i,
                        titles[i] if i < len(titles) else "",
                        files[i] if i < len(files) else "",
                        docs_urls[i] if i < len(docs_urls) else "",
                        summaries_json[i] if i < len(summaries_json) else None,
                    ),
                )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist apply_job_findings for %s", apply_id, exc_info=True)
        finally:
            conn.close()

    def update_apply_job_finding_status(self, apply_id: str, ordinal: int, status: str) -> None:
        """Update the status of a single apply_job_finding by ordinal."""
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE apply_job_findings SET status = ? WHERE apply_job_id = ? AND ordinal = ?",
                (status, apply_id, ordinal),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to update apply_job_finding status", exc_info=True)
        finally:
            conn.close()

    def persist_apply_event(self, apply_id: str, event_type: str, payload: dict | None = None) -> None:
        """Append an event to apply_events."""
        import json as _json
        conn = get_connection()
        try:
            # Use BEGIN IMMEDIATE to prevent concurrent readers from getting
            # the same MAX(sequence_no) before our INSERT completes.
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence_no), -1) + 1 as next_seq FROM apply_events WHERE apply_job_id = ?",
                (apply_id,),
            ).fetchone()
            seq = row["next_seq"] if row else 0

            conn.execute(
                """INSERT INTO apply_events (id, apply_job_id, sequence_no, event_type, created_at, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), apply_id, seq, event_type,
                    datetime.now(timezone.utc).isoformat(),
                    _json.dumps(payload) if payload else None,
                ),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist apply event for %s", apply_id, exc_info=True)
        finally:
            conn.close()

    def _persist_apply_create(self, apply: ApplyResult) -> None:
        repo_id, ws_id, _git_info = ensure_repository_and_workspace(apply.project_path)
        now = datetime.now(timezone.utc).isoformat()
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO apply_jobs
                   (id, repository_id, workspace_id, project_path, status, started_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (apply.apply_id, repo_id, ws_id, apply.project_path, apply.status, now),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist apply creation for %s", apply.apply_id, exc_info=True)
        finally:
            conn.close()

    def _persist_apply_update(self, apply: ApplyResult) -> None:
        """Persist intermediate field updates (pr_branch, status changes, etc.)."""
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE apply_jobs
                   SET status = ?, pr_url = ?, pr_branch = ?, pr_error = ?,
                       started_at = COALESCE(?, started_at)
                   WHERE id = ?""",
                (
                    apply.status,
                    apply.pr_url, apply.pr_branch, apply.pr_error,
                    apply.started_at.isoformat() if apply.started_at else None,
                    apply.apply_id,
                ),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist apply update for %s", apply.apply_id, exc_info=True)
        finally:
            conn.close()

    def _persist_apply_complete(self, apply: ApplyResult) -> None:
        now = datetime.now(timezone.utc).isoformat()
        duration_ms = None
        if apply.started_at and apply.completed_at:
            duration_ms = int((apply.completed_at - apply.started_at).total_seconds() * 1000)

        conn = get_connection()
        try:
            conn.execute(
                """UPDATE apply_jobs
                   SET status = ?, completed_at = ?, duration_ms = ?,
                       error_text = ?, pr_url = ?, pr_branch = ?, pr_error = ?
                   WHERE id = ?""",
                (
                    apply.status,
                    apply.completed_at.isoformat() if apply.completed_at else now,
                    duration_ms,
                    apply.error,
                    apply.pr_url, apply.pr_branch, apply.pr_error,
                    apply.apply_id,
                ),
            )
            conn.commit()
        except Exception:
            logger.warning("Failed to persist apply completion for %s", apply.apply_id, exc_info=True)
        finally:
            conn.close()

    def _load_apply_from_db(self, apply_id: str) -> ApplyResult | None:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM apply_jobs WHERE id = ?", (apply_id,)).fetchone()
            if row is None:
                return None

            apply = ApplyResult(
                apply_id=apply_id,
                project_path=row["project_path"],
                status=row["status"],
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                error=row["error_text"],
                pr_url=row["pr_url"],
                pr_branch=row["pr_branch"],
                pr_error=row["pr_error"],
            )

            self._applies[apply_id] = apply
            return apply
        except Exception:
            logger.warning("Failed to load apply %s from database", apply_id, exc_info=True)
            return None
        finally:
            conn.close()


# Singletons
store = ScanStore()
apply_store = ApplyStore()
