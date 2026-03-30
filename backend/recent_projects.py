from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any
from urllib.parse import unquote, urlparse

from models import ProjectSource, RecentProject

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURSOR_STORAGE_PATH = Path.home() / "Library/Application Support/Cursor/User/globalStorage/storage.json"
VSCODE_STORAGE_PATH = Path.home() / "Library/Application Support/Code/User/globalStorage/storage.json"
VSCODE_STATE_DB_PATH = Path.home() / "Library/Application Support/Code/User/globalStorage/state.vscdb"
CLAUDE_SESSIONS_DIR = Path.home() / ".claude" / "sessions"
SAMPLE_PROJECTS = (
    ("⭐️ Sample project: Support ticket classifier", PROJECT_ROOT / "sample_project"),
)
SOURCE_ORDER = {
    ProjectSource.SAMPLE_PROJECT: 0,
    ProjectSource.CURSOR: 1,
    ProjectSource.VSCODE: 2,
    ProjectSource.CLAUDE_CODE: 3,
}
RECENT_PROJECTS_CACHE_TTL_SECONDS = 15.0
_recent_projects_cache: dict[int, tuple[float, list[RecentProject]]] = {}
_recent_projects_cache_lock = Lock()


@dataclass
class _CollectedProject:
    path: Path
    recent_rank: int | None = None
    last_used_at: datetime | None = None
    sources: set[ProjectSource] = field(default_factory=set)
    name: str | None = None


def list_recent_projects(limit: int = 10) -> list[RecentProject]:
    now = monotonic()
    with _recent_projects_cache_lock:
        cached = _recent_projects_cache.get(limit)
        if cached and now - cached[0] < RECENT_PROJECTS_CACHE_TTL_SECONDS:
            return [project.model_copy(deep=True) for project in cached[1]]

    projects = _collect_recent_projects(limit)

    with _recent_projects_cache_lock:
        _recent_projects_cache[limit] = (now, projects)

    return [project.model_copy(deep=True) for project in projects]


def _collect_recent_projects(limit: int) -> list[RecentProject]:
    collected: dict[Path, _CollectedProject] = {}
    _merge_editor_projects(collected, ProjectSource.CURSOR, CURSOR_STORAGE_PATH)
    _merge_editor_projects(collected, ProjectSource.VSCODE, VSCODE_STORAGE_PATH, VSCODE_STATE_DB_PATH)
    _merge_claude_projects(collected)
    sample_project_paths = _merge_sample_projects(collected)

    # Enrich projects that lack a timestamp with actual directory activity
    for item in collected.values():
        if item.last_used_at is None:
            item.last_used_at = _get_directory_last_activity(item.path)

    ordered = sorted(collected.values(), key=_sort_key)
    sample_project_path_set = set(sample_project_paths)
    prioritized = [collected[path] for path in sample_project_paths if path in collected]
    prioritized.extend(item for item in ordered if item.path not in sample_project_path_set)
    projects: list[RecentProject] = []
    for item in prioritized[:limit]:
        projects.append(
            RecentProject(
                path=str(item.path),
                name=item.name or item.path.name or str(item.path),
                last_used_at=item.last_used_at,
                sources=sorted(item.sources, key=lambda source: SOURCE_ORDER[source]),
            )
        )
    return projects


def _merge_editor_projects(
    collected: dict[Path, _CollectedProject],
    source: ProjectSource,
    storage_path: Path,
    state_db_path: Path | None = None,
) -> None:
    paths = _load_editor_recent_paths(storage_path, state_db_path)
    for rank, path in enumerate(paths):
        item = collected.setdefault(path, _CollectedProject(path=path))
        if item.recent_rank is None or rank < item.recent_rank:
            item.recent_rank = rank
        item.sources.add(source)


def _merge_claude_projects(collected: dict[Path, _CollectedProject]) -> None:
    if not CLAUDE_SESSIONS_DIR.exists():
        return

    try:
        session_files = sorted(
            CLAUDE_SESSIONS_DIR.glob("*.json"),
            key=lambda file_path: file_path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return

    for session_file in session_files:
        data = _read_json(session_file)
        if not data:
            continue

        path = _normalize_directory(data.get("cwd"))
        if path is None:
            continue

        item = collected.setdefault(path, _CollectedProject(path=path))
        item.sources.add(ProjectSource.CLAUDE_CODE)

        started_at = _timestamp_ms_to_datetime(data.get("startedAt"))
        if started_at and (item.last_used_at is None or started_at > item.last_used_at):
            item.last_used_at = started_at


def _merge_sample_projects(collected: dict[Path, _CollectedProject]) -> list[Path]:
    sample_project_paths: list[Path] = []
    for name, path in SAMPLE_PROJECTS:
        try:
            resolved_path = path.resolve()
        except OSError:
            continue

        if not resolved_path.is_dir():
            continue

        item = collected.setdefault(resolved_path, _CollectedProject(path=resolved_path))
        item.name = name
        item.sources.add(ProjectSource.SAMPLE_PROJECT)
        sample_project_paths.append(resolved_path)

    return sample_project_paths


def _load_editor_recent_paths(storage_path: Path, state_db_path: Path | None = None) -> list[Path]:
    data = _read_json(storage_path)
    candidate_paths: list[str] = []
    if data:
        candidate_paths.extend(_editor_recent_folder_candidates(data))

    if not candidate_paths and state_db_path is not None:
        candidate_paths.extend(_read_recent_paths_from_state_db(state_db_path))

    seen: set[Path] = set()
    ordered_paths: list[Path] = []

    for raw_path in candidate_paths:
        path = _normalize_directory(raw_path)
        if path is None or path in seen:
            continue
        seen.add(path)
        ordered_paths.append(path)

    return ordered_paths


def _editor_recent_folder_candidates(data: dict[str, Any]) -> list[str]:
    candidates: list[str] = []

    menu_items = (
        data.get("lastKnownMenubarData", {})
        .get("menus", {})
        .get("File", {})
        .get("items", [])
    )
    for item in menu_items:
        if item.get("id") != "submenuitem.MenubarRecentMenu":
            continue
        for submenu_item in item.get("submenu", {}).get("items", []):
            if submenu_item.get("id") != "openRecentFolder":
                continue
            path = _path_from_uri_payload(submenu_item.get("uri"))
            if path:
                candidates.append(path)

    if candidates:
        return candidates

    windows_state = data.get("windowsState", {})
    last_active = _path_from_uri_payload(windows_state.get("lastActiveWindow", {}).get("folder"))
    if last_active:
        candidates.append(last_active)

    for window in windows_state.get("openedWindows", []):
        path = _path_from_uri_payload(window.get("folder"))
        if path:
            candidates.append(path)

    for folder in data.get("backupWorkspaces", {}).get("folders", []):
        path = _path_from_uri_payload(folder.get("folderUri"))
        if path:
            candidates.append(path)

    return candidates


def _read_recent_paths_from_state_db(state_db_path: Path) -> list[str]:
    if not state_db_path.exists():
        return []

    try:
        connection = sqlite3.connect(f"file:{state_db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return []

    try:
        row = connection.execute(
            "SELECT value FROM ItemTable WHERE key = ?",
            ("history.recentlyOpenedPathsList",),
        ).fetchone()
    except sqlite3.Error:
        connection.close()
        return []

    connection.close()
    if not row or not isinstance(row[0], str):
        return []

    try:
        data = json.loads(row[0])
    except json.JSONDecodeError:
        return []

    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return []

    candidates: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = _path_from_uri_payload(entry.get("folderUri"))
        if path:
            candidates.append(path)

    return candidates


def _path_from_uri_payload(payload: Any) -> str | None:
    if isinstance(payload, dict):
        if payload.get("scheme") != "file":
            return None
        raw_path = payload.get("path")
        return raw_path if isinstance(raw_path, str) else None

    if isinstance(payload, str):
        parsed = urlparse(payload)
        if parsed.scheme != "file":
            return None
        return unquote(parsed.path)

    return None


def _get_directory_last_activity(path: Path) -> datetime | None:
    """Get the last activity time for a directory, preferring git commit time."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            unix_ts = int(result.stdout.strip())
            return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass

    # Fall back to directory modification time
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc)
    except OSError:
        return None


def _normalize_directory(raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    try:
        path = Path(raw_path).expanduser().resolve()
    except OSError:
        return None

    if not path.is_dir():
        return None

    return path

def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _timestamp_ms_to_datetime(value: Any) -> datetime | None:
    if not isinstance(value, int):
        return None

    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _sort_key(item: _CollectedProject) -> tuple[float, int]:
    """Sort by recency first, then by editor rank as tiebreaker."""
    timestamp = item.last_used_at.timestamp() if item.last_used_at else 0.0
    rank = item.recent_rank if item.recent_rank is not None else 9999
    return (-timestamp, rank)
