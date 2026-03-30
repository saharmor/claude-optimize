from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from models import Finding, ProjectSummary
from settings import get_bool_env, get_env, get_int_env

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 300
MAX_TURNS = get_int_env("CLAUDE_OPTIMIZE_MAX_TURNS", default=12, min_value=1)
MODEL_NAME = get_env("CLAUDE_OPTIMIZE_MODEL", default="sonnet")
SKIP_PERMISSIONS = get_bool_env("CLAUDE_OPTIMIZE_SKIP_PERMISSIONS", default=False)


async def run_analyzer(prompt: str, project_path: str) -> list[Finding]:
    """Run a Claude Code headless session and parse structured findings."""
    result_text = await _run_claude_prompt(prompt, project_path)
    findings = _parse_findings(result_text)
    logger.info("Parsed %d findings from analyzer response (%d chars)", len(findings), len(result_text))
    return findings


async def run_project_summary(prompt: str, project_path: str) -> ProjectSummary:
    """Run a Claude Code session and parse a structured project summary."""
    result_text = await _run_claude_prompt(prompt, project_path)
    summary = _parse_project_summary(result_text)
    logger.info("Parsed project summary (%d chars)", len(result_text))
    return summary


async def _run_claude_prompt(prompt: str, project_path: str) -> str:
    """Run a Claude Code headless session and return the raw result text."""
    command = [
        "claude",
        "--print",
        "--output-format",
        "json",
        "--model",
        MODEL_NAME,
        "--max-turns",
        str(MAX_TURNS),
    ]
    if SKIP_PERMISSIONS:
        command.append("--dangerously-skip-permissions")
    command.extend(["-p", prompt])

    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=project_path,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"Analyzer timed out after {TIMEOUT_SECONDS}s")

    if proc.returncode != 0:
        err = stderr.decode() if stderr else "Unknown error"
        raise RuntimeError(f"Claude Code exited with code {proc.returncode}: {err}")

    raw = stdout.decode()

    try:
        envelope = json.loads(raw)
        subtype = envelope.get("subtype", "")
        if subtype == "error_max_turns":
            logger.warning(
                "Analyzer hit max turns limit (session %s, %s turns). "
                "Attempting to extract partial results.",
                envelope.get("session_id", "?"),
                envelope.get("num_turns", "?"),
            )
        result_text = envelope.get("result", "")
        if not result_text or not isinstance(result_text, str):
            result_text = raw
    except json.JSONDecodeError:
        result_text = raw

    return result_text


def _normalize_finding(raw: dict) -> dict:
    """Normalize common field variations from Claude's output."""
    VALID_SEVERITIES = {"high", "medium", "low"}

    if "impact" in raw and isinstance(raw["impact"], dict):
        for field in ("cost_reduction", "latency_reduction", "reliability_improvement"):
            val = raw["impact"].get(field, "low")
            if isinstance(val, str):
                val = val.lower().strip()
            if val not in VALID_SEVERITIES:
                raw["impact"][field] = "low"

    for field in ("confidence", "effort"):
        val = raw.get(field, "")
        if isinstance(val, str):
            val = val.lower().strip()
        if val not in VALID_SEVERITIES:
            raw[field] = "medium"

    if "category" in raw and isinstance(raw["category"], str):
        raw["category"] = raw["category"].lower().strip().replace(" ", "_")

    # Ensure model field is a string (default to empty if missing)
    raw.setdefault("model", "")
    if not isinstance(raw["model"], str):
        raw["model"] = str(raw["model"])

    for block_key in ("current_state", "suggested_fix"):
        block = raw.get(block_key)
        if isinstance(block, dict) and "language" not in block:
            block["language"] = _detect_language(raw.get("location"))

    loc = raw.get("location")
    if isinstance(loc, dict):
        loc["lines"] = loc.get("lines") or ""
        loc["function"] = loc.get("function") or ""

    rec = raw.get("recommendation")
    if isinstance(rec, dict):
        rec.setdefault("docs_url", "")

    return raw


def _detect_language(location: dict | None) -> str:
    if not isinstance(location, dict):
        return "text"

    file_path = location.get("file", "")
    suffix = Path(file_path).suffix.lower()
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "jsx",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "bash",
    }.get(suffix, "text")


def _validate_findings(items: list[dict]) -> list[Finding]:
    """Validate a list of raw dicts into Finding objects, skipping invalid ones."""
    findings: list[Finding] = []
    for i, raw in enumerate(items):
        try:
            normalized = _normalize_finding(raw)
            findings.append(Finding.model_validate(normalized))
        except Exception as e:
            logger.warning("Finding %d failed validation: %s; raw keys: %s", i, e, list(raw.keys()))
    return findings


def _extract_json_arrays(text: str) -> list[str]:
    """Extract balanced JSON arrays from arbitrary text."""
    candidates: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False

    for i, char in enumerate(text):
        if start is None:
            if char == "[":
                start = i
                depth = 1
                in_string = False
                escaped = False
            continue

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                candidates.append(text[start : i + 1])
                start = None

    return candidates


def _extract_json_objects(text: str) -> list[str]:
    """Extract balanced JSON objects from arbitrary text."""
    candidates: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False

    for i, char in enumerate(text):
        if start is None:
            if char == "{":
                start = i
                depth = 1
                in_string = False
                escaped = False
            continue

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidates.append(text[start : i + 1])
                start = None

    return candidates


def _parse_findings(text: str) -> list[Finding]:
    """Extract a JSON array of findings from Claude's response text."""
    # Try direct parse first
    try:
        data = json.loads(text)
        if isinstance(data, list):
            findings = _validate_findings(data)
            if findings:
                return findings
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fences
    patterns = [
        r"```json\s*\n([\s\S]*?)\n```",
        r"```\s*\n([\s\S]*?)\n```",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1) if match.lastindex else match.group(0)
            try:
                data = json.loads(candidate)
                if isinstance(data, list):
                    findings = _validate_findings(data)
                    if findings:
                        return findings
            except json.JSONDecodeError:
                continue

    # Try extracting any balanced JSON array from prose-heavy output
    for candidate in _extract_json_arrays(text):
        try:
            data = json.loads(candidate)
            if isinstance(data, list):
                findings = _validate_findings(data)
                if findings:
                    return findings
        except json.JSONDecodeError:
            continue

    logger.warning("No findings could be parsed. Response preview: %.500s", text)
    return []


def _parse_project_summary(text: str) -> ProjectSummary:
    """Extract a JSON object project summary from Claude's response text."""

    def _validate_summary(candidate: object) -> ProjectSummary | None:
        if not isinstance(candidate, dict):
            return None
        try:
            return ProjectSummary.model_validate(candidate)
        except Exception:
            return None

    try:
        data = json.loads(text)
        summary = _validate_summary(data)
        if summary:
            return summary
    except json.JSONDecodeError:
        pass

    patterns = [
        r"```json\s*\n([\s\S]*?)\n```",
        r"```\s*\n([\s\S]*?)\n```",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = match.group(1) if match.lastindex else match.group(0)
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        summary = _validate_summary(data)
        if summary:
            return summary

    for candidate in _extract_json_objects(text):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        summary = _validate_summary(data)
        if summary:
            return summary

    raise RuntimeError("Project summary response could not be parsed as JSON")
