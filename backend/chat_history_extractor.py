"""Extract user messages from Claude Code and Cursor chat history.

Claude Code stores conversation history at:
  ~/.claude/projects/<encoded-project-path>/<session-uuid>.jsonl

Cursor stores data in SQLite databases (.vscdb files):
  Workspace DBs: ~/Library/Application Support/Cursor/User/workspaceStorage/<hash>/state.vscdb
  Global chat DB: ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Claude Code paths
# ---------------------------------------------------------------------------
CLAUDE_DIR = Path.home() / ".claude" / "projects"

# ---------------------------------------------------------------------------
# Cursor paths (macOS)
# ---------------------------------------------------------------------------
_CURSOR_BASE = Path.home() / "Library" / "Application Support" / "Cursor" / "User"
_CURSOR_WORKSPACE_STORAGE = _CURSOR_BASE / "workspaceStorage"
_CURSOR_GLOBAL_DB_CANDIDATES = [
    _CURSOR_BASE / "globalStorage" / "state.vscdb",
    _CURSOR_BASE / "globalStorage" / "cursor.cursor" / "state.vscdb",
    _CURSOR_BASE / "globalStorage" / "cursor" / "state.vscdb",
]

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

# Intent clustering
CLUSTER_SIMILARITY_THRESHOLD = 0.3
_MAX_CLUSTER_EXAMPLES = 3

STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "be", "as", "was", "are",
    "this", "that", "these", "those", "i", "my", "me", "we", "you", "your",
    "can", "do", "does", "did", "will", "would", "should", "could",
    "have", "has", "had", "not", "no", "so", "if", "then", "than",
    "all", "also", "just", "about", "up", "out", "into",
    "please", "make", "sure", "want", "need", "like", "use",
})

# Limits to avoid reading too much data from disk
_MAX_JSONL_FILES = 200
_MAX_TOTAL_BYTES = 200 * 1024 * 1024  # 200 MB


@dataclass
class ExtractedMessage:
    session_id: str
    text: str
    timestamp: str


@dataclass
class MessageCluster:
    """A group of semantically similar messages."""
    seed_tokens: frozenset[str]
    messages: list[ExtractedMessage]  # unique messages in this cluster
    exact_dupe_count: int  # total count including exact duplicates


_TOKENIZE_RE = re.compile(r"\W+")


def _tokenize(text: str) -> frozenset[str]:
    """Tokenize text into a set of meaningful lowercase words."""
    tokens = _TOKENIZE_RE.split(text.lower())
    result = frozenset(t for t in tokens if len(t) >= 2 and t not in STOP_WORDS)
    return result if result else frozenset({text.lower().strip()})


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity: size of intersection / size of union."""
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


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


def _cluster_messages(
    messages: list[ExtractedMessage],
    threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
) -> tuple[list[MessageCluster], list[ExtractedMessage]]:
    """Cluster messages by Jaccard similarity using greedy centroid-absorb.

    Returns (multi_clusters, singletons) where multi_clusters have ≥2 unique
    messages or ≥2 exact duplicates, and singletons are ungrouped messages.
    """
    # Step 1: exact dedup with frequency counting
    seen: dict[str, int] = {}
    unique: list[ExtractedMessage] = []
    for msg in messages:
        key = msg.text.strip().lower()
        if key in seen:
            seen[key] += 1
        else:
            seen[key] = 1
            unique.append(msg)

    # Step 2: sort by frequency desc (so high-frequency messages become seeds)
    unique.sort(key=lambda m: seen[m.text.strip().lower()], reverse=True)

    # Step 3: greedy centroid-absorb clustering
    clusters: list[MessageCluster] = []
    for msg in unique:
        tokens = _tokenize(msg.text)
        freq = seen[msg.text.strip().lower()]

        best_sim = 0.0
        best_cluster: MessageCluster | None = None
        for cluster in clusters:
            sim = _jaccard(tokens, cluster.seed_tokens)
            if sim > best_sim:
                best_sim = sim
                best_cluster = cluster

        if best_sim >= threshold and best_cluster is not None:
            best_cluster.messages.append(msg)
            best_cluster.exact_dupe_count += freq
        else:
            clusters.append(MessageCluster(
                seed_tokens=tokens,
                messages=[msg],
                exact_dupe_count=freq,
            ))

    # Step 4: split into multi-message clusters and singletons
    multi = [c for c in clusters if len(c.messages) >= 2 or c.exact_dupe_count >= 2]
    singletons = [
        c.messages[0] for c in clusters
        if len(c.messages) == 1 and c.exact_dupe_count == 1
    ]
    return multi, singletons


def _extract_claude_code_messages(project_path: str) -> list[ExtractedMessage]:
    """Extract user messages from Claude Code JSONL chat history."""
    dir_name = _project_path_to_dir_name(project_path)
    history_dir = CLAUDE_DIR / dir_name

    if not history_dir.is_dir():
        logger.info("No Claude Code chat history found for project: %s", project_path)
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

    logger.info("Claude Code: extracted %d messages", len(messages))
    return messages


# ---------------------------------------------------------------------------
# Cursor extraction helpers
# ---------------------------------------------------------------------------

def _cursor_safe_query(
    db_path: Path, query: str, params: tuple = (),
) -> list[sqlite3.Row] | None:
    """Execute a read-only SQLite query, returning rows or None on error."""
    if not db_path.exists():
        return None
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return rows
    except Exception as e:
        logger.debug("Cursor DB query failed on %s: %s", db_path, e)
        return None
    finally:
        if conn is not None:
            conn.close()


def _cursor_uri_to_path(uri: str) -> str | None:
    """Convert a file:// URI to a filesystem path."""
    try:
        parsed = urlparse(uri)
        if parsed.scheme == "file":
            return unquote(parsed.path)
        return unquote(uri)
    except Exception:
        return None


def _cursor_find_workspace_ids(target_project: str) -> list[str]:
    """Find Cursor workspace IDs whose folder matches the target project."""
    target = os.path.realpath(target_project).rstrip("/")
    if not _CURSOR_WORKSPACE_STORAGE.exists():
        return []

    matches: list[str] = []
    for ws_dir in _CURSOR_WORKSPACE_STORAGE.iterdir():
        workspace_json = ws_dir / "workspace.json"
        if not workspace_json.exists():
            continue
        try:
            data = json.loads(workspace_json.read_text())
            folder = data.get("folder")
            if not folder:
                continue
            p = _cursor_uri_to_path(folder)
            if not p:
                continue
            resolved = os.path.realpath(p).rstrip("/")
            if resolved == target:
                matches.append(ws_dir.name)
        except Exception:
            continue

    return matches


def _cursor_get_composer_ids(workspace_id: str) -> set[str]:
    """Read composer IDs from a Cursor workspace's state.vscdb."""
    db_path = _CURSOR_WORKSPACE_STORAGE / workspace_id / "state.vscdb"
    rows = _cursor_safe_query(
        db_path,
        "SELECT value FROM ItemTable WHERE key = ?",
        ("composer.composerData",),
    )
    if not rows:
        return set()
    try:
        val = rows[0]["value"]
        if isinstance(val, bytes):
            val = val.decode("utf-8", errors="replace")
        data = json.loads(val)
        return {
            c["composerId"]
            for c in data.get("allComposers", [])
            if "composerId" in c
        }
    except (json.JSONDecodeError, TypeError, KeyError):
        return set()


def _cursor_find_global_db() -> Path | None:
    """Locate the global Cursor state.vscdb."""
    for candidate in _CURSOR_GLOBAL_DB_CANDIDATES:
        if candidate.exists():
            return candidate
    gs = _CURSOR_BASE / "globalStorage"
    if gs.exists():
        for p in gs.rglob("state.vscdb"):
            return p
    return None


def _extract_cursor_messages(project_path: str) -> list[ExtractedMessage]:
    """Extract user messages from Cursor chat history for the given project."""
    if not _CURSOR_BASE.exists():
        return []

    workspace_ids = _cursor_find_workspace_ids(project_path)
    if not workspace_ids:
        logger.info("No Cursor workspace found for project: %s", project_path)
        return []

    composer_ids: set[str] = set()
    for ws_id in workspace_ids:
        composer_ids |= _cursor_get_composer_ids(ws_id)

    if not composer_ids:
        logger.info("No Cursor composers found for project: %s", project_path)
        return []

    global_db = _cursor_find_global_db()
    if not global_db:
        return []

    rows = _cursor_safe_query(
        global_db,
        "SELECT key, value FROM cursorDiskKV WHERE key LIKE ?",
        ("bubbleId:%",),
    )
    if not rows:
        return []

    messages: list[ExtractedMessage] = []
    for row in rows:
        key = row["key"]
        parts = key.split(":")
        if len(parts) < 3:
            continue
        composer_id = parts[1]
        if composer_id not in composer_ids:
            continue

        val = row["value"]
        if val is None:
            continue
        if isinstance(val, bytes):
            val = val.decode("utf-8", errors="replace")
        try:
            d = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            continue

        if d.get("type") != 1:  # only user messages
            continue
        text = (d.get("text") or "").strip()
        if len(text) < _MIN_MESSAGE_LENGTH:
            continue

        messages.append(ExtractedMessage(
            session_id=f"cursor-{composer_id}",
            text=text,
            timestamp="",
        ))

    logger.info("Cursor: extracted %d messages from %d composers", len(messages), len(composer_ids))
    return messages


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_messages(project_path: str) -> list[ExtractedMessage]:
    """Extract all user messages from both Claude Code and Cursor history."""
    cc_messages = _extract_claude_code_messages(project_path)
    cursor_messages = _extract_cursor_messages(project_path)
    combined = cc_messages + cursor_messages
    logger.info(
        "Total extracted: %d messages (Claude Code: %d, Cursor: %d)",
        len(combined), len(cc_messages), len(cursor_messages),
    )
    return combined


def format_messages_for_prompt(messages: list[ExtractedMessage]) -> str:
    """Format extracted messages as pre-clustered intent groups for the LLM.

    Uses Jaccard similarity to cluster messages by intent, then formats as:
    - Intent clusters (with count + representative examples)
    - Unclustered singleton messages (most recent first)
    """
    if not messages:
        return "(No chat history found for this project.)"

    clusters, singletons = _cluster_messages(messages)

    # Sort clusters by total message count descending
    clusters.sort(key=lambda c: c.exact_dupe_count, reverse=True)

    lines: list[str] = []
    lines.append(f"Total user messages: {len(messages)}")
    lines.append(f"Intent clusters: {len(clusters)}")
    lines.append(f"Unclustered messages: {len(singletons)}")
    lines.append(f"Sessions: {len(set(m.session_id for m in messages))}")
    lines.append("")

    # Clusters first — pick shortest messages as representatives (clearest intent)
    for cluster in clusters:
        lines.append(f"=== Intent cluster ({cluster.exact_dupe_count} messages across sessions) ===")
        lines.append("Examples:")
        reps = sorted(cluster.messages, key=lambda m: len(m.text))[:_MAX_CLUSTER_EXAMPLES]
        for rep in reps:
            text = rep.text if len(rep.text) <= 300 else rep.text[:300] + "..."
            lines.append(f'  - "{text}"')
        lines.append("")

    # Singletons — most recent first, capped by remaining budget
    singletons.reverse()
    remaining = max(MAX_MESSAGES_FOR_PROMPT - sum(c.exact_dupe_count for c in clusters), 20)
    for msg in singletons[:remaining]:
        text = msg.text if len(msg.text) <= 500 else msg.text[:500] + "..."
        lines.append(f"--- Unclustered message (session: {msg.session_id[:8]}) ---")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)
