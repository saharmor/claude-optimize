from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from analyzers import ANALYZER_PROMPTS
from claude_runner import run_analyzer, run_project_summary
from demo_findings import DEMO_FINDINGS as SAMPLE_PROJECT_FINDINGS
from models import AnalyzerStatus, AnalyzerType, Finding
from project_summary import DEMO_PROJECT_SUMMARY, build_project_summary_prompt
from report_builder import build_report
from settings import get_int_env
from store import store

_SAMPLE_PROJECT_PATH = (Path(__file__).resolve().parent.parent / "sample_project").resolve()

# Staggered delays (seconds) for each analyzer in sample project mode so the UI shows
# realistic incremental progress. Total wall-clock time stays under 20 s.
_SAMPLE_PROJECT_DELAYS: dict[AnalyzerType, float] = {
    AnalyzerType.PROMPT_ENGINEERING: 3.0,
    AnalyzerType.PROMPT_CACHING: 6.0,
    AnalyzerType.BATCHING: 10.0,
    AnalyzerType.TOOL_USE: 13.0,
    AnalyzerType.STRUCTURED_OUTPUTS: 16.0,
}

_SAMPLE_PROJECT_FINDINGS_BY_TYPE: dict[AnalyzerType, list[Finding]] = {}
for _f in SAMPLE_PROJECT_FINDINGS:
    _SAMPLE_PROJECT_FINDINGS_BY_TYPE.setdefault(_f.category, []).append(_f)

MAX_CONCURRENT_SCANS = get_int_env(
    "CLAUDE_OPTIMIZE_MAX_CONCURRENT_SCANS",
    default=2,
    min_value=1,
)
SCAN_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_SCANS)


async def run_scan(scan_id: str, project_path: str) -> None:
    """Run all 5 analyzers in parallel and aggregate results."""
    summary_task = asyncio.create_task(_run_project_summary(scan_id, project_path))

    try:
        async with SCAN_SEMAPHORE:
            tasks = {}
            for analyzer_type, prompt_builder in ANALYZER_PROMPTS.items():
                prompt = prompt_builder()
                tasks[analyzer_type] = asyncio.create_task(
                    _run_single_analyzer(scan_id, analyzer_type, prompt, project_path)
                )

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        failed_analyzers = 0
        for analyzer_type, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                failed_analyzers += 1

        scan = store.get(scan_id)
        if scan:
            scan.completed_at = datetime.now(timezone.utc)
            if failed_analyzers == len(tasks):
                scan.status = "failed"
                scan.error = "All analyzers failed. Check Claude CLI configuration and permissions."
            else:
                scan.status = "completed"
                if failed_analyzers:
                    scan.error = f"{failed_analyzers} analyzer(s) failed, but partial results are available."

        store.notify(scan_id, {
            "event": "scan_complete",
            "data": {
                "scan_id": scan_id,
                "total_findings": len(scan.findings) if scan else 0,
                "status": scan.status if scan else "failed",
                "error": scan.error if scan else None,
            },
        })

    except Exception as e:
        scan = store.update(
            scan_id,
            status="failed",
            error=str(e),
            completed_at=datetime.now(timezone.utc),
        )
        store.notify(scan_id, {
            "event": "scan_complete",
            "data": {
                "scan_id": scan_id,
                "status": "failed",
                "error": str(e),
                "total_findings": len(scan.findings) if scan else 0,
            },
        })
    finally:
        await summary_task
        _notify_stream_complete_if_ready(scan_id)


def is_sample_project(project_path: str) -> bool:
    """Return True when project_path points to the sample project."""
    try:
        return Path(project_path).resolve() == _SAMPLE_PROJECT_PATH
    except OSError:
        return False


async def run_sample_project_scan(scan_id: str, project_path: str) -> None:
    """Fast sample project mode: replay pre-generated findings with staggered delays.

    Each analyzer fires sequentially with a short sleep so the UI shows
    realistic incremental progress. Total time is under 20 seconds.
    """
    summary_task = asyncio.create_task(_run_sample_project_summary(scan_id))

    try:
        tasks = [
            asyncio.create_task(
                _run_sample_project_analyzer(scan_id, analyzer_type)
            )
            for analyzer_type in AnalyzerType
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        scan = store.get(scan_id)
        if scan:
            scan.completed_at = datetime.now(timezone.utc)
            scan.status = "completed"

        store.notify(scan_id, {
            "event": "scan_complete",
            "data": {
                "scan_id": scan_id,
                "total_findings": len(scan.findings) if scan else 0,
                "status": "completed",
                "error": None,
            },
        })
    except Exception as e:
        scan = store.update(
            scan_id,
            status="failed",
            error=str(e),
            completed_at=datetime.now(timezone.utc),
        )
        store.notify(scan_id, {
            "event": "scan_complete",
            "data": {
                "scan_id": scan_id,
                "status": "failed",
                "error": str(e),
                "total_findings": 0,
            },
        })
    finally:
        await summary_task
        _notify_stream_complete_if_ready(scan_id)


async def _run_sample_project_analyzer(
    scan_id: str,
    analyzer_type: AnalyzerType,
) -> list[Finding]:
    """Simulate a single sample project analyzer with a pre-set delay."""
    store.update_analyzer_status(scan_id, analyzer_type, AnalyzerStatus.RUNNING)
    await asyncio.sleep(_SAMPLE_PROJECT_DELAYS.get(analyzer_type, 5.0))
    findings = _SAMPLE_PROJECT_FINDINGS_BY_TYPE.get(analyzer_type, [])
    _store_analyzer_findings(scan_id, findings)
    store.update_analyzer_status(scan_id, analyzer_type, AnalyzerStatus.COMPLETED)
    store.notify(scan_id, {
        "event": "analyzer_complete",
        "data": {
            "analyzer": analyzer_type.value,
            "finding_count": len(findings),
        },
    })
    return findings


async def _run_single_analyzer(
    scan_id: str,
    analyzer_type: AnalyzerType,
    prompt: str,
    project_path: str,
) -> list[Finding]:
    """Run a single analyzer and update its status in the store."""
    store.update_analyzer_status(scan_id, analyzer_type, AnalyzerStatus.RUNNING)

    try:
        findings = await run_analyzer(prompt, project_path)
        _store_analyzer_findings(scan_id, findings)
        store.update_analyzer_status(scan_id, analyzer_type, AnalyzerStatus.COMPLETED)
        # Notify with finding count
        store.notify(scan_id, {
            "event": "analyzer_complete",
            "data": {
                "analyzer": analyzer_type.value,
                "finding_count": len(findings),
            },
        })
        return findings
    except Exception as exc:
        store.update_analyzer_status(scan_id, analyzer_type, AnalyzerStatus.FAILED)
        store.update_analyzer_error(scan_id, analyzer_type, str(exc))
        raise


async def _run_project_summary(scan_id: str, project_path: str) -> None:
    store.update_project_summary_status(scan_id, AnalyzerStatus.RUNNING)

    try:
        summary = await run_project_summary(build_project_summary_prompt(), project_path)
        store.set_project_summary(scan_id, summary)
        store.update_project_summary_status(scan_id, AnalyzerStatus.COMPLETED)
        store.notify(scan_id, {
            "event": "project_summary_complete",
            "data": {
                "one_liner": summary.one_liner,
                "description": summary.description,
            },
        })
    except Exception as exc:
        store.set_project_summary_error(scan_id, str(exc))
        store.update_project_summary_status(scan_id, AnalyzerStatus.FAILED)
        store.notify(scan_id, {
            "event": "project_summary_failed",
            "data": {"error": str(exc)},
        })


async def _run_sample_project_summary(scan_id: str) -> None:
    try:
        store.update_project_summary_status(scan_id, AnalyzerStatus.RUNNING)
        await asyncio.sleep(19.0)
        store.set_project_summary(scan_id, DEMO_PROJECT_SUMMARY)
        store.update_project_summary_status(scan_id, AnalyzerStatus.COMPLETED)
        store.notify(scan_id, {
            "event": "project_summary_complete",
            "data": DEMO_PROJECT_SUMMARY.model_dump(),
        })
    except Exception as exc:
        logger.exception("Sample project summary failed for scan %s", scan_id)
        store.set_project_summary_error(scan_id, str(exc))
        store.update_project_summary_status(scan_id, AnalyzerStatus.FAILED)
        store.notify(scan_id, {
            "event": "project_summary_failed",
            "data": {"error": str(exc)},
        })


def _store_analyzer_findings(scan_id: str, findings: list[Finding]) -> None:
    scan = store.add_findings(scan_id, findings)
    if scan:
        scan.scorecard = build_report(scan.findings)


def _notify_stream_complete_if_ready(scan_id: str) -> None:
    if not store.is_stream_complete(scan_id):
        return

    scan = store.get(scan_id)
    store.notify(scan_id, {
        "event": "stream_complete",
        "data": {
            "scan_id": scan_id,
            "status": scan.status if scan else "failed",
            "error": scan.error if scan else None,
            "total_findings": len(scan.findings) if scan else 0,
        },
    })
