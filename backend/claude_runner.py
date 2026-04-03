from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from models import Finding, ProjectSummary
from settings import get_bool_env, get_env, get_int_env

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 600
MAX_TURNS = get_int_env("CLAUDE_OPTIMIZE_MAX_TURNS", default=12, min_value=1)
MODEL_NAME = get_env("CLAUDE_OPTIMIZE_MODEL", default="opus")
SKIP_PERMISSIONS = get_bool_env("CLAUDE_OPTIMIZE_SKIP_PERMISSIONS", default=False)


_FILE_TOOLS = {"Edit", "Write", "NotebookEdit"}


async def run_apply(
    prompt: str,
    project_path: str,
    on_output: Callable[[str], None] | None = None,
    on_tool_use: Callable[[str, str], None] | None = None,
) -> str:
    """Run Claude Code to apply changes to a project, streaming structured events.

    *on_output* is called with each line of text output from Claude.
    *on_tool_use* is called with (tool_name, file_path) when a file-editing
    tool is invoked, allowing callers to track per-file progress.
    """
    command = [
        "claude",
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
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

    output_lines: list[str] = []
    result_text: str = ""

    async def _stream_stdout():
        nonlocal result_text
        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode().rstrip("\n")
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # Non-JSON output — treat as plain text
                output_lines.append(line)
                if on_output:
                    on_output(line)
                continue

            event_type = event.get("type")

            if event_type == "assistant":
                # Extract text content and tool_use blocks
                msg = event.get("message", {})
                for block in msg.get("content", []):
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        for text_line in text.splitlines():
                            output_lines.append(text_line)
                            if on_output:
                                on_output(text_line)
                    elif block.get("type") == "tool_use":
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})
                        file_path = tool_input.get("file_path", "")
                        # Forward file-editing tool use for finding progress tracking
                        if tool_name in _FILE_TOOLS and file_path and on_tool_use:
                            on_tool_use(tool_name, file_path)
                        # Show tool activity as output so the user sees progress
                        if on_output:
                            if file_path:
                                on_output(f"Using {tool_name} on {file_path}...")
                            elif tool_name in ("Bash", "Glob", "Grep", "Read"):
                                # Show non-file tools too for visibility
                                cmd = tool_input.get("command", "")
                                pattern = tool_input.get("pattern", "")
                                detail = cmd[:80] if cmd else pattern[:80] if pattern else ""
                                if detail:
                                    on_output(f"Running {tool_name}: {detail}")
                                else:
                                    on_output(f"Running {tool_name}...")

            elif event_type == "result":
                result_text = event.get("result", "")
                if event.get("is_error") or event.get("subtype") == "error_max_turns":
                    logger.warning("Apply stream result: subtype=%s", event.get("subtype"))

    stderr_lines: list[bytes] = []

    async def _stream_stderr():
        assert proc.stderr is not None
        async for raw_line in proc.stderr:
            stderr_lines.append(raw_line)

    try:
        await asyncio.wait_for(
            asyncio.gather(_stream_stdout(), _stream_stderr()),
            timeout=TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"Apply timed out after {TIMEOUT_SECONDS}s")
    except Exception:
        proc.kill()
        await proc.communicate()
        raise

    await proc.wait()

    if proc.returncode != 0:
        if stderr_lines:
            err = b"".join(stderr_lines).decode().strip()
        else:
            err = "Unknown error (check server logs for full output)"
        raise RuntimeError(f"Claude Code exited with code {proc.returncode}: {err}")

    return result_text or "\n".join(output_lines)


_NO_CLAUDE_PATTERNS = [
    "does not use the anthropic",
    "does not use the claude",
    "doesn't use the anthropic",
    "doesn't use the claude",
    "no anthropic",
    "no claude api",
    "no imports of the `anthropic`",
    "no `anthropic` imports",
    "not claude",
    "not using claude",
    "not using the anthropic",
]


def _detect_no_claude_usage(text: str) -> str | None:
    """Return a user-facing note if the analyzer says there's no Claude API usage."""
    lower = text.lower()
    for pattern in _NO_CLAUDE_PATTERNS:
        if pattern in lower:
            return "no_claude_usage"
    return None


@dataclass
class AnalyzerResult:
    """Rich result from running an analyzer, including metadata for persistence."""
    findings: list[Finding] = field(default_factory=list)
    note: str | None = None
    prompt_hash: str | None = None
    model_name: str | None = None
    raw_output: str | None = None


async def run_analyzer(prompt: str, project_path: str) -> AnalyzerResult:
    """Run a Claude Code headless session and parse structured findings.

    Returns an AnalyzerResult with findings, optional note, and metadata
    for persistence (prompt hash, model name, raw output).
    """
    result_text = await _run_claude_prompt(prompt, project_path)
    findings = _parse_findings(result_text)
    note = _detect_no_claude_usage(result_text) if not findings else None
    logger.info("Parsed %d findings from analyzer response (%d chars), note=%s", len(findings), len(result_text), note)

    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    return AnalyzerResult(
        findings=findings,
        note=note,
        prompt_hash=prompt_hash,
        model_name=MODEL_NAME,
        raw_output=result_text,
    )


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
        err_stderr = stderr.decode().strip() if stderr else ""
        err_stdout = stdout.decode().strip() if stdout else ""
        err = err_stderr or err_stdout or "Unknown error"
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

    # Fix misplaced content: if suggested_fix.code_snippet is empty but
    # description contains what looks like file content (YAML frontmatter,
    # markdown headers, code), swap them so the apply step gets usable content.
    sf = raw.get("suggested_fix")
    if isinstance(sf, dict):
        snippet = (sf.get("code_snippet") or "").strip()
        desc = (sf.get("description") or "").strip()
        if not snippet and desc and _looks_like_code_content(desc):
            sf["code_snippet"] = desc
            sf["description"] = "Apply suggested changes"

    loc = raw.get("location")
    if isinstance(loc, dict):
        loc["lines"] = loc.get("lines") or ""
        loc["function"] = loc.get("function") or ""

    rec = raw.get("recommendation")
    if isinstance(rec, dict):
        rec.setdefault("docs_url", "")

    return raw


def _looks_like_code_content(text: str) -> bool:
    """Heuristic: does this text look like code/file content rather than prose?"""
    # YAML frontmatter (SKILL.md, config files)
    if text.startswith("---"):
        return True
    # Markdown headers or code fences
    if text.startswith("#") or text.startswith("```"):
        return True
    # Contains multiple newlines and indentation (structured content)
    lines = text.split("\n")
    if len(lines) >= 5:
        indented = sum(1 for l in lines if l.startswith("  ") or l.startswith("\t"))
        if indented >= len(lines) * 0.3:
            return True
    return False


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
