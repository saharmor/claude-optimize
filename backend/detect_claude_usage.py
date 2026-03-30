"""Fast filesystem-based check for Claude API usage in a project.

Scans source files for anthropic SDK imports, Claude model identifiers,
and messages.create calls. Returns True if any indicator is found.
This avoids running expensive Claude CLI analyzers on projects that
don't use the Claude API at all.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# File extensions worth scanning
_SOURCE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".java", ".rb", ".rs",
    ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".env",
}

# Directories to skip
_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "env", ".env", "dist", "build", ".next", ".nuxt",
    "vendor", "target", ".tox", ".mypy_cache", ".pytest_cache",
    "site-packages",
}

# Max file size to read (256 KB) — skip large generated files
_MAX_FILE_SIZE = 256 * 1024

# Patterns that indicate Claude API usage (case-insensitive)
_PATTERNS = [
    re.compile(r"""import\s+anthropic""", re.IGNORECASE),
    re.compile(r"""from\s+anthropic""", re.IGNORECASE),
    re.compile(r"""require\s*\(\s*['"]@anthropic-ai/sdk['"]\s*\)"""),
    re.compile(r"""from\s+['"]@anthropic-ai/sdk['"]"""),
    re.compile(r"""anthropic\.Anthropic"""),
    re.compile(r"""new\s+Anthropic\s*\("""),
    re.compile(r"""messages\.create\s*\("""),
    re.compile(r"""claude-(?:opus|sonnet|haiku|3|instant)""", re.IGNORECASE),
    re.compile(r"""claude_(?:opus|sonnet|haiku)""", re.IGNORECASE),
    re.compile(r"""ANTHROPIC_API_KEY"""),
    re.compile(r"""anthropic_api_key""", re.IGNORECASE),
    re.compile(r"""x-api-key.*anthropic""", re.IGNORECASE),
    re.compile(r"""api\.anthropic\.com"""),
]

# Max number of files to scan before giving up and assuming "maybe"
_MAX_FILES = 5000


def has_claude_usage(project_path: str) -> bool:
    """Return True if the project appears to use the Anthropic Claude API."""
    root = Path(project_path)
    if not root.is_dir():
        return True  # can't check, assume yes

    files_scanned = 0

    for path in _walk_source_files(root):
        if files_scanned >= _MAX_FILES:
            logger.info(
                "Pre-check: scanned %d files without conclusion, assuming Claude usage possible",
                files_scanned,
            )
            return True

        try:
            if path.stat().st_size > _MAX_FILE_SIZE:
                continue
            content = path.read_text(errors="ignore")
        except OSError:
            continue

        files_scanned += 1

        for pattern in _PATTERNS:
            if pattern.search(content):
                logger.info("Pre-check: Claude API usage detected in %s", path)
                return True

    logger.info("Pre-check: no Claude API usage found after scanning %d files", files_scanned)
    return False


def _walk_source_files(root: Path):
    """Yield source files under root, skipping irrelevant directories."""
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return

    for entry in entries:
        if entry.is_symlink():
            continue
        if entry.name.startswith(".") and entry.name not in (".env",):
            if entry.is_dir():
                continue
        if entry.is_dir():
            if entry.name in _SKIP_DIRS:
                continue
            yield from _walk_source_files(entry)
        elif entry.is_file() and entry.suffix.lower() in _SOURCE_EXTENSIONS:
            yield entry
