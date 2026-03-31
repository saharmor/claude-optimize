"""Fast filesystem-based check for Claude API usage in a project.

Scans source files for anthropic SDK imports, Claude model identifiers,
and messages.create calls. Returns True if any indicator is found.
This avoids running expensive Claude CLI analyzers on projects that
don't use the Claude API at all.

Detection uses a tiered approach:
- Strong patterns (direct SDK imports, API calls) → immediate True
- Weak patterns (env var names, model strings) → need 2+ different categories
- Composite triggers (LiteLLM, OpenRouter) + model name → True
- .env files with actual API key values → promoted to strong
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

# ---------------------------------------------------------------------------
# Tier 1 – Strong patterns: any single match confirms Claude API usage
# ---------------------------------------------------------------------------
_STRONG_PATTERNS = [
    # Direct Anthropic SDK imports (Python)
    re.compile(r"""import\s+anthropic\b""", re.IGNORECASE),
    re.compile(r"""from\s+anthropic\b""", re.IGNORECASE),

    # Direct Anthropic SDK imports (JavaScript / TypeScript)
    re.compile(r"""require\s*\(\s*['"]@anthropic-ai/sdk['"]\s*\)"""),
    re.compile(r"""from\s+['"]@anthropic-ai/sdk['"]"""),

    # SDK constructor calls
    re.compile(r"""anthropic\.Anthropic\s*\("""),
    re.compile(r"""new\s+Anthropic\s*\("""),

    # API call pattern (specific to Anthropic SDK)
    re.compile(r"""messages\.create\s*\("""),

    # Direct HTTP calls to Anthropic API
    re.compile(r"""api\.anthropic\.com"""),

    # --- Third-party wrapper: LangChain ---
    re.compile(r"""from\s+langchain_anthropic"""),
    re.compile(r"""from\s+langchain\.chat_models.*import.*ChatAnthropic"""),
    re.compile(r"""ChatAnthropic\s*\("""),

    # --- Third-party wrapper: Vercel AI SDK ---
    re.compile(r"""from\s+['"]@ai-sdk/anthropic['"]"""),
    re.compile(r"""require\s*\(\s*['"]@ai-sdk/anthropic['"]\s*\)"""),

    # --- Third-party wrapper: AWS Bedrock with Claude ---
    re.compile(r"""anthropic\.claude"""),  # Bedrock model ID pattern
]

# ---------------------------------------------------------------------------
# Tier 2 – Weak patterns: need 2+ different categories to confirm usage
# ---------------------------------------------------------------------------
# Each entry is (category, compiled_regex)
_WEAK_PATTERNS: list[tuple[str, re.Pattern]] = [
    # api_key – could just be env var forwarding
    ("api_key", re.compile(r"""ANTHROPIC_API_KEY""")),
    ("api_key", re.compile(r"""anthropic_api_key""", re.IGNORECASE)),

    # model_name – could be in docs / comments / config for non-API use
    ("model_name", re.compile(r"""claude-(?:opus|sonnet|haiku|3|instant)""", re.IGNORECASE)),
    ("model_name", re.compile(r"""claude_(?:opus|sonnet|haiku)""", re.IGNORECASE)),

    # header – could be generic HTTP header reference
    ("header", re.compile(r"""x-api-key.*anthropic""", re.IGNORECASE)),
]

# ---------------------------------------------------------------------------
# .env file – ANTHROPIC_API_KEY with an actual value is a strong signal
# ---------------------------------------------------------------------------
_ENV_STRONG_PATTERNS = [
    re.compile(r"""ANTHROPIC_API_KEY\s*=\s*\S+"""),
]

# ---------------------------------------------------------------------------
# Composite triggers – multi-provider libraries that need a Claude model
# name nearby to confirm Claude-specific usage
# ---------------------------------------------------------------------------
_COMPOSITE_TRIGGERS = [
    re.compile(r"""import\s+litellm"""),
    re.compile(r"""from\s+litellm"""),
    re.compile(r"""openrouter""", re.IGNORECASE),
    re.compile(r"""vertex_ai/claude""", re.IGNORECASE),
]

# Max number of files to scan before giving up and assuming "maybe"
_MAX_FILES = 5000


def has_claude_usage(project_path: str) -> bool:
    """Return True if the project appears to use the Anthropic Claude API."""
    root = Path(project_path)
    if not root.is_dir():
        return True  # can't check, assume yes

    files_scanned = 0
    weak_categories_seen: set[str] = set()
    has_composite_trigger = False

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

        # 1. Strong patterns – any match is conclusive
        for pattern in _STRONG_PATTERNS:
            if pattern.search(content):
                logger.info("Pre-check: Claude API usage detected (strong) in %s", path)
                return True

        # 2. .env files – actual key value is strong
        if path.name == ".env" or path.name.endswith(".env"):
            for pattern in _ENV_STRONG_PATTERNS:
                if pattern.search(content):
                    logger.info("Pre-check: Claude API key found in %s", path)
                    return True

        # 3. Composite triggers (litellm, openrouter, vertex)
        if not has_composite_trigger:
            for pattern in _COMPOSITE_TRIGGERS:
                if pattern.search(content):
                    has_composite_trigger = True
                    break

        # 4. Weak patterns – accumulate categories
        for category, pattern in _WEAK_PATTERNS:
            if category not in weak_categories_seen and pattern.search(content):
                weak_categories_seen.add(category)

    # After scanning all files: evaluate accumulated signals
    if has_composite_trigger and "model_name" in weak_categories_seen:
        logger.info(
            "Pre-check: Claude usage detected via composite trigger + model name reference"
        )
        return True

    if len(weak_categories_seen) >= 2:
        logger.info(
            "Pre-check: Claude usage detected via multiple weak signals: %s",
            weak_categories_seen,
        )
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
