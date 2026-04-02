"""Extract user messages from Claude Code chat history JSONL files.

Claude Code stores conversation history at:
  ~/.claude/projects/<encoded-project-path>/<session-uuid>.jsonl

Each JSONL file contains one conversation session with records like:
  {"type": "user", "message": {"role": "user", "content": "..."}, ...}
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CLAUDE_DIR = Path.home() / ".claude" / "projects"

# Known XML tag names injected by Claude Code. We match these specifically
# rather than using a generic <...>...</...> regex that mishandles nesting.
_CLAUDE_XML_TAGS = (
    "ide_selection", "ide_opened_file", "system-reminder", "local-command-caveat",
    "local-command-stdout", "local-command-stderr", "command-name", "command-message",
    "command-args", "context", "user-prompt-submit-hook",
)
_XML_BLOCK_RE = re.compile(
    r"<(" + "|".join(re.escape(t) for t in _CLAUDE_XML_TAGS) + r")\b[^>]*>.*?</\1>",
    re.DOTALL,
)
_XML_SELF_CLOSING_RE = re.compile(
    r"<(" + "|".join(re.escape(t) for t in _CLAUDE_XML_TAGS) + r")\b[^>]*/?>",
)

# Prefixes to check on the RAW content (before XML stripping)
_RAW_SKIP_PREFIXES = (
    "<command-name>",
    "<local-command",
)

# Prefixes to check on CLEANED content (after XML stripping)
_CLEANED_SKIP_PREFIXES = (
    "exit",
    "See ya",
    "/exit",
    "/memory",
    "/permissions",
    "/help",
    "/clear",
    "/compact",
    "[Request interrupted",
)

# Substrings that indicate system-generated / automated prompts (not user-typed)
_AUTOMATED_INDICATORS = (
    "You are an expert code analyzer for the Claude Optimize tool",
    "You are an expert analyzer for the Claude Optimize tool",
    "You are analyzing a local codebase to explain what the project does",
    "# Claude API Optimization Tasks",
    "Return ONLY a valid JSON array of findings",
)

# Minimum length for a message to be considered substantial
_MIN_MESSAGE_LENGTH = 20

# Maximum messages to embed in the prompt (to stay within context limits)
MAX_MESSAGES_FOR_PROMPT = 150

# Limits to avoid reading too much data from disk
_MAX_JSONL_FILES = 200
_MAX_TOTAL_BYTES = 50 * 1024 * 1024  # 50 MB


@dataclass
class ExtractedMessage:
    session_id: str
    text: str
    timestamp: str


def _project_path_to_dir_name(project_path: str) -> str:
    """Convert a project path to Claude's encoded directory name.

    e.g. /Users/saharmor/Documents/codebase/genaisf
      -> -Users-saharmor-Documents-codebase-genaisf

    Claude Code uses the resolved absolute path with slashes replaced by dashes,
    keeping the leading dash from the root slash.
    """
    normalized = str(Path(project_path).resolve())
    return normalized.replace("/", "-")


def _clean_message(content: str) -> str:
    """Strip known Claude Code XML tags and whitespace from message content."""
    cleaned = _XML_BLOCK_RE.sub("", content)
    cleaned = _XML_SELF_CLOSING_RE.sub("", cleaned)
    return cleaned.strip()


def _should_skip_raw(raw_content: str) -> bool:
    """Check the raw (pre-cleaning) content for XML-based skip patterns."""
    for prefix in _RAW_SKIP_PREFIXES:
        if raw_content.startswith(prefix):
            return True
    for indicator in _AUTOMATED_INDICATORS:
        if indicator in raw_content:
            return True
    return False


def _should_skip_cleaned(cleaned: str) -> bool:
    """Check cleaned content for commands, short messages, etc."""
    for prefix in _CLEANED_SKIP_PREFIXES:
        if cleaned.startswith(prefix):
            return True
    return len(cleaned) < _MIN_MESSAGE_LENGTH


def _extract_user_text(content: str | list) -> str | None:
    """Extract user text from message content (can be str or list)."""
    if isinstance(content, str):
        if _should_skip_raw(content):
            return None
        cleaned = _clean_message(content)
        if not cleaned or _should_skip_cleaned(cleaned):
            return None
        return cleaned
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                raw_text = item.get("text", "")
                if _should_skip_raw(raw_text):
                    continue
                cleaned = _clean_message(raw_text)
                if cleaned and not _should_skip_cleaned(cleaned):
                    parts.append(cleaned)
        combined = "\n".join(parts)
        return combined if combined and len(combined) >= _MIN_MESSAGE_LENGTH else None
    return None


def extract_messages(project_path: str) -> list[ExtractedMessage]:
    """Extract all user messages from chat history for the given project."""
    dir_name = _project_path_to_dir_name(project_path)
    history_dir = CLAUDE_DIR / dir_name

    if not history_dir.is_dir():
        logger.info("No chat history found for project: %s", project_path)
        return []

    messages: list[ExtractedMessage] = []
    total_bytes_read = 0

    jsonl_files = sorted(history_dir.glob("*.jsonl"))[:_MAX_JSONL_FILES]

    for jsonl_file in jsonl_files:
        if total_bytes_read >= _MAX_TOTAL_BYTES:
            logger.info("Hit byte limit (%d MB), stopping early", _MAX_TOTAL_BYTES // (1024 * 1024))
            break

        session_id = jsonl_file.stem
        try:
            file_size = jsonl_file.stat().st_size
            total_bytes_read += file_size
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if record.get("type") != "user":
                        continue

                    msg = record.get("message", {})
                    content = msg.get("content", "")
                    timestamp = record.get("timestamp", "")

                    text = _extract_user_text(content)
                    if text:
                        messages.append(ExtractedMessage(
                            session_id=session_id,
                            text=text,
                            timestamp=str(timestamp),
                        ))
        except Exception:
            logger.warning("Failed to read session file: %s", jsonl_file, exc_info=True)

    return messages


def format_messages_for_prompt(messages: list[ExtractedMessage]) -> str:
    """Format extracted messages into a string suitable for embedding in a prompt.

    Truncates to MAX_MESSAGES_FOR_PROMPT and adds session context.
    """
    if not messages:
        return "(No chat history found for this project.)"

    # Deduplicate exact matches while preserving count
    seen: dict[str, int] = {}
    unique_messages: list[ExtractedMessage] = []
    for msg in messages:
        normalized = msg.text.strip().lower()
        if normalized in seen:
            seen[normalized] += 1
        else:
            seen[normalized] = 1
            unique_messages.append(msg)

    # Show repeated messages first (sorted by frequency), then fill remaining
    # slots with recent unique messages to surface complex one-off workflows.
    repeated = [m for m in unique_messages if seen[m.text.strip().lower()] > 1]
    repeated.sort(key=lambda m: seen[m.text.strip().lower()], reverse=True)
    singles = [m for m in unique_messages if seen[m.text.strip().lower()] == 1]
    # Singles are already in file-order (chronological); show most recent first
    singles.reverse()
    selected = (repeated + singles)[:MAX_MESSAGES_FOR_PROMPT]

    lines = []
    lines.append(f"Total user messages: {len(messages)}")
    lines.append(f"Unique messages: {len(unique_messages)}")
    lines.append(f"Sessions: {len(set(m.session_id for m in messages))}")
    lines.append("")

    for msg in selected:
        count = seen[msg.text.strip().lower()]
        count_label = f" [repeated {count}x]" if count > 1 else ""
        # Truncate very long messages
        text = msg.text if len(msg.text) <= 500 else msg.text[:500] + "..."
        lines.append(f"--- Message{count_label} (session: {msg.session_id[:8]}) ---")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)
