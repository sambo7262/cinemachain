"""Masking and scrubbing utilities for API key security."""
from __future__ import annotations

import traceback as _traceback

# Mutable list populated at startup with live key values for log scrubbing.
_active_secrets: list[str] = []


def mask_key(value: str | None) -> str | None:
    """Return ***abc format (last 3 chars). None -> None. Short values -> ***."""
    if value is None:
        return None
    if len(value) < 4:
        return "***"
    return "***" + value[-3:]


def is_masked_sentinel(value: str | None) -> bool:
    """True if value is a masked sentinel (starts with *** and total length <= 10)."""
    if not value:
        return False
    return value.startswith("***") and len(value) <= 10


def scrub_text(text: str, secrets: list[str]) -> str:
    """Replace all occurrences of each secret in text with [REDACTED]. Skips secrets < 4 chars."""
    for secret in secrets:
        if secret and len(secret) >= 4:
            text = text.replace(secret, "[REDACTED]")
    return text


def register_secret(value: str) -> None:
    """Register a live secret value so the log filter can scrub it. No-op for duplicates."""
    if value and value not in _active_secrets:
        _active_secrets.append(value)


def clear_secrets() -> None:
    """Clear all registered secrets. Used in tests only."""
    _active_secrets.clear()


def scrub_traceback(exc: BaseException | None = None) -> str:
    """
    Format the current exception traceback (or the given exc) and scrub all registered secrets.
    Use at logger.exception() / logger.error() call sites where exc context could contain keys.

    Usage:
        except Exception as exc:
            safe_tb = scrub_traceback(exc)
            logger.error("Context msg\\n%s", safe_tb)
            # Do NOT use logger.exception() here — that would emit the unscrubbed traceback
    """
    if exc is not None:
        tb_str = "".join(_traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        tb_str = _traceback.format_exc()
    return scrub_text(tb_str, _active_secrets)
