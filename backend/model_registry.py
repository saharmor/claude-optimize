"""Loads the model registry markdown file and exposes section accessors.

The registry (model_registry.md) is the single source of truth for model
identifiers, pricing, capabilities, upgrade paths, and breaking changes.
It is read once at import time and injected into analyzer prompts.
"""

from __future__ import annotations

from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent / "model_registry.md"
_registry_text: str | None = None


def _load() -> str:
    global _registry_text
    if _registry_text is None:
        _registry_text = _REGISTRY_PATH.read_text()
    return _registry_text


def get_full_registry() -> str:
    """Return the entire registry as a string for injection into prompts."""
    return _load()


def get_section(heading: str) -> str:
    """Extract a single top-level (##) section by its heading text.

    Returns the section content (excluding the heading line itself),
    up to but not including the next ## heading or end of file.
    """
    registry = _load()
    marker = f"## {heading}"
    start = registry.find(marker)
    if start == -1:
        return ""
    # Skip past the heading line
    start = registry.index("\n", start) + 1
    # Find the next ## heading (or end of file)
    next_section = registry.find("\n## ", start)
    if next_section == -1:
        return registry[start:].strip()
    return registry[start:next_section].strip()
