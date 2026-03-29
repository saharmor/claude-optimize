from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def get_env(key: str, default: str) -> str:
    """Return an environment variable value, falling back to default."""
    value = os.getenv(key)
    if value:
        return value
    return default


def get_int_env(key: str, default: int, min_value: int | None = None) -> int:
    """Return an integer env var, warning and falling back when invalid."""
    raw_value = get_env(key, str(default))
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid value for %s: %r. Falling back to %d.",
            key,
            raw_value,
            default,
        )
        return default

    if min_value is not None and parsed < min_value:
        logger.warning(
            "Value for %s must be >= %d, got %d. Falling back to %d.",
            key,
            min_value,
            parsed,
            default,
        )
        return default

    return parsed


def get_bool_env(key: str, default: bool = False) -> bool:
    """Return a boolean env var using common truthy strings."""
    raw_value = get_env(key, "true" if default else "false")
    return raw_value.lower() in {"1", "true", "yes"}
