from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from models import AnalyzerStatus, AnalyzerType, ApplyResult, Finding, ProjectSummary, ScanResult
from settings import get_int_env

SCAN_TTL_SECONDS = get_int_env(
    "CLAUDE_OPTIMIZE_SCAN_TTL_SECONDS",
    default=3600,
    min_value=0,
)


class ScanStore:
    """In-memory store for scan state. Maps scan_id -> ScanResult."""

    def __init__(self) -> None:
        self._scans: dict[str, ScanResult] = {}
        # SSE subscribers: scan_id -> list of asyncio.Queue
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def create(self, scan: ScanResult) -> None:
        self._cleanup_expired()
        self._scans[scan.scan_id] = scan

    def get(self, scan_id: str) -> ScanResult | None:
        self._cleanup_expired()
        return self._scans.get(scan_id)

    def update(self, scan_id: str, **kwargs) -> ScanResult | None:
        scan = self._scans.get(scan_id)
        if scan is None:
            return None
        for key, value in kwargs.items():
            setattr(scan, key, value)
        return scan

    def add_findings(self, scan_id: str, findings: list[Finding]) -> ScanResult | None:
        scan = self._scans.get(scan_id)
        if scan is None:
            return None
        scan.findings.extend(findings)
        return scan

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
        return scan

    def set_project_summary_error(self, scan_id: str, error: str) -> ScanResult | None:
        scan = self._scans.get(scan_id)
        if scan is None:
            return None
        scan.project_summary_error = error
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
        self._cleanup_expired()
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

    def _cleanup_expired(self) -> None:
        if SCAN_TTL_SECONDS <= 0:
            return

        now = datetime.now(timezone.utc)
        expired_scan_ids: list[str] = []

        for scan_id, scan in self._scans.items():
            if scan.status not in {"completed", "failed"}:
                continue

            completed_at = scan.completed_at or scan.started_at
            if completed_at is None:
                continue

            age_seconds = (now - completed_at).total_seconds()
            if age_seconds > SCAN_TTL_SECONDS:
                expired_scan_ids.append(scan_id)

        for scan_id in expired_scan_ids:
            self._scans.pop(scan_id, None)
            self._subscribers.pop(scan_id, None)


class ApplyStore:
    """In-memory store for apply jobs. Maps apply_id -> ApplyResult."""

    def __init__(self) -> None:
        self._applies: dict[str, ApplyResult] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def create(self, apply: ApplyResult) -> None:
        self._cleanup_expired()
        self._applies[apply.apply_id] = apply

    def get(self, apply_id: str) -> ApplyResult | None:
        return self._applies.get(apply_id)

    def update(self, apply_id: str, **kwargs) -> ApplyResult | None:
        apply = self._applies.get(apply_id)
        if apply is None:
            return None
        for key, value in kwargs.items():
            setattr(apply, key, value)
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

    def _cleanup_expired(self) -> None:
        if SCAN_TTL_SECONDS <= 0:
            return

        now = datetime.now(timezone.utc)
        expired: list[str] = []

        for apply_id, apply in self._applies.items():
            if apply.status not in {"completed", "failed"}:
                continue
            completed_at = apply.completed_at or apply.started_at
            if completed_at is None:
                continue
            if (now - completed_at).total_seconds() > SCAN_TTL_SECONDS:
                expired.append(apply_id)

        for apply_id in expired:
            self._applies.pop(apply_id, None)
            self._subscribers.pop(apply_id, None)


# Singletons
store = ScanStore()
apply_store = ApplyStore()
