from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from models import AnalyzerStatus, AnalyzerType, ScanResult
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

    def subscribe(self, scan_id: str) -> asyncio.Queue:
        self._cleanup_expired()
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(scan_id, []).append(queue)
        scan = self._scans.get(scan_id)
        if scan and scan.status in {"completed", "failed"}:
            queue.put_nowait(
                {
                    "event": "scan_complete",
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


# Singleton
store = ScanStore()
