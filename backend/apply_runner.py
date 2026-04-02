from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from claude_runner import run_apply
from git_pr import create_pull_request, get_changed_files, snapshot_changed_files
from store import apply_store

logger = logging.getLogger(__name__)

APPLY_SEMAPHORE = asyncio.Semaphore(1)

_SAMPLE_PROJECT_PATH = (Path(__file__).resolve().parent.parent / "sample_project").resolve()


def _is_sample_project(project_path: str) -> bool:
    try:
        return Path(project_path).resolve() == _SAMPLE_PROJECT_PATH
    except OSError:
        return False


async def _mock_apply(on_output: Callable[[str], None]) -> None:
    """Simulate a realistic Claude Code apply session without touching any files."""
    steps = [
        (0.4, "Reading project structure..."),
        (0.6, ""),
        (0.8, "Identified files to modify:"),
        (0.3, "  - src/api/client.ts"),
        (0.2, "  - src/services/claude.py"),
        (0.2, "  - src/utils/prompt.ts"),
        (0.7, ""),
        (1.0, "Applying prompt caching optimizations..."),
        (0.5, "  Adding cache_control headers to system prompts"),
        (0.8, "  Restructuring message array for cache efficiency"),
        (0.4, ""),
        (1.2, "Applying batching improvements..."),
        (0.5, "  Converting sequential API calls to batch requests"),
        (0.6, "  Added batch result aggregation"),
        (0.4, ""),
        (0.9, "Applying model selection optimizations..."),
        (0.5, "  Switching classification tasks to Haiku"),
        (0.4, "  Keeping complex reasoning on Sonnet"),
        (0.4, ""),
        (0.8, "Running validation checks..."),
        (0.6, "  All type checks passed"),
        (0.4, "  No breaking changes detected"),
        (0.5, ""),
        (0.3, "Done. Applied optimizations to 3 files."),
    ]

    for delay, line in steps:
        await asyncio.sleep(delay + random.uniform(-0.1, 0.15))
        on_output(line)


async def run_apply_job(apply_id: str, prompt: str, project_path: str, finding_titles: list[str] | None = None) -> None:
    """Run Claude Code to apply selected findings to the project."""
    async with APPLY_SEMAPHORE:
        apply_store.update(apply_id, status="running", started_at=datetime.now(timezone.utc))
        apply_store.notify(apply_id, {
            "event": "apply_status",
            "data": {"status": "running"},
        })

        try:
            # Build lowercase keywords for matching output lines to findings
            titles = finding_titles or []
            # Extract significant keywords (3+ chars) from each finding title
            finding_keywords: list[list[str]] = []
            for title in titles:
                words = [w.lower() for w in title.split() if len(w) >= 3]
                finding_keywords.append(words)
            current_finding_index = -1

            def _check_finding_progress(line: str) -> None:
                nonlocal current_finding_index
                if not titles:
                    return
                lower_line = line.lower()
                # Check each finding after the current one
                for idx in range(current_finding_index + 1, len(titles)):
                    keywords = finding_keywords[idx]
                    # Match if line contains enough keywords from the finding title
                    if not keywords:
                        continue
                    matched = sum(1 for kw in keywords if kw in lower_line)
                    if matched >= min(2, len(keywords)):
                        # Mark previous finding as done
                        if current_finding_index >= 0:
                            apply_store.notify(apply_id, {
                                "event": "finding_progress",
                                "data": {"index": current_finding_index, "status": "done"},
                            })
                        current_finding_index = idx
                        apply_store.notify(apply_id, {
                            "event": "finding_progress",
                            "data": {"index": idx, "status": "applying"},
                        })
                        break

            def on_output(line: str) -> None:
                apply_store.notify(apply_id, {
                    "event": "apply_output",
                    "data": {"line": line},
                })
                _check_finding_progress(line)

            is_sample = _is_sample_project(project_path)

            # Snapshot dirty files BEFORE the apply so we can diff afterward
            files_before: set[str] = set()
            if not is_sample:
                files_before = await snapshot_changed_files(project_path)

            if is_sample:
                await _mock_apply(on_output)
                # Simulate per-finding progress for sample project
                for idx in range(len(titles)):
                    apply_store.notify(apply_id, {
                        "event": "finding_progress",
                        "data": {"index": idx, "status": "done"},
                    })
            else:
                await run_apply(prompt, project_path, on_output=on_output)

            # Attempt to create a PR (skip for sample project)
            if not is_sample:
                changed_files = await get_changed_files(project_path, files_before)

                apply_store.notify(apply_id, {
                    "event": "creating_pr",
                    "data": {"apply_id": apply_id},
                })
                on_output("")
                on_output("Creating pull request...")

                branch_name = f"claude-optimize/{apply_id}"
                apply_store.update(apply_id, pr_branch=branch_name)
                pr_title = "Claude Optimize: Apply optimizations"
                pr_body = "Optimizations applied by [Claude Optimize](https://github.com/anthropics/claude-optimize)."

                try:
                    url = await create_pull_request(
                        project_path, branch_name, pr_title, pr_body,
                        changed_files=changed_files, on_output=on_output,
                    )
                    apply_store.update(apply_id, pr_url=url)
                    apply_store.notify(apply_id, {
                        "event": "pr_created",
                        "data": {"apply_id": apply_id, "pr_url": url},
                    })
                except Exception as pr_exc:
                    logger.warning("PR creation failed for %s: %s", apply_id, pr_exc)
                    apply_store.update(apply_id, pr_error=str(pr_exc))
                    apply_store.notify(apply_id, {
                        "event": "pr_failed",
                        "data": {"apply_id": apply_id, "error": str(pr_exc)},
                    })

            # Mark final finding as done
            if current_finding_index >= 0:
                apply_store.notify(apply_id, {
                    "event": "finding_progress",
                    "data": {"index": current_finding_index, "status": "done"},
                })

            apply_store.update(
                apply_id,
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
            apply_store.notify(apply_id, {
                "event": "apply_complete",
                "data": {"apply_id": apply_id, "status": "completed"},
            })
        except Exception as exc:
            logger.exception("Apply job %s failed", apply_id)
            apply_store.update(
                apply_id,
                status="failed",
                error=str(exc),
                completed_at=datetime.now(timezone.utc),
            )
            apply_store.notify(apply_id, {
                "event": "apply_failed",
                "data": {"apply_id": apply_id, "error": str(exc)},
            })
        finally:
            apply = apply_store.get(apply_id)
            apply_store.notify(apply_id, {
                "event": "stream_complete",
                "data": {
                    "apply_id": apply_id,
                    "status": apply.status if apply else "failed",
                    "error": apply.error if apply else None,
                },
            })
