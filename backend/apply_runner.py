from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from claude_runner import run_apply
from store import apply_store

logger = logging.getLogger(__name__)

APPLY_SEMAPHORE = asyncio.Semaphore(1)


async def run_apply_job(apply_id: str, prompt: str, project_path: str) -> None:
    """Run Claude Code to apply selected findings to the project."""
    async with APPLY_SEMAPHORE:
        apply_store.update(apply_id, status="running", started_at=datetime.now(timezone.utc))
        apply_store.notify(apply_id, {
            "event": "apply_status",
            "data": {"status": "running"},
        })

        try:
            def on_output(line: str) -> None:
                apply_store.notify(apply_id, {
                    "event": "apply_output",
                    "data": {"line": line},
                })

            await run_apply(prompt, project_path, on_output=on_output)

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
