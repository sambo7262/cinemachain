"""Root logging filter that scrubs API key patterns and registered secrets from all log output."""
from __future__ import annotations

import logging
import re

from app.utils.masking import _active_secrets, scrub_text

# Regex patterns that scrub known key-bearing patterns regardless of registered secrets.
# These catch cases where keys haven't been registered yet (e.g., early startup logs).
_PATTERN_SCRUBS: list[tuple[re.Pattern, str]] = [
    # api_key= / apikey= query params (case-insensitive)
    (re.compile(r'(?i)(api_?key=)[A-Za-z0-9_\-]{8,}'), r'\1[REDACTED]'),
    # Authorization: Bearer <token>
    (re.compile(r'(?i)(Authorization:\s*Bearer\s+)\S+'), r'\1[REDACTED]'),
    # X-Api-Key header value
    (re.compile(r'(?i)(X-Api-Key[:\s]+)[A-Za-z0-9_\-]{8,}'), r'\1[REDACTED]'),
]


def _apply_patterns(text: str) -> str:
    for pattern, replacement in _PATTERN_SCRUBS:
        text = pattern.sub(replacement, text)
    return text


def _scrub(text: str) -> str:
    text = _apply_patterns(text)
    return scrub_text(text, _active_secrets)


class ScrubSecretsFilter(logging.Filter):
    """
    Logging filter that scrubs API key values from log records before they are written.

    Install on the root logger (not just handlers) so it catches records from all modules:
        logging.getLogger().addFilter(ScrubSecretsFilter())

    Secrets must be registered via register_secret() in app.utils.masking before they
    can be scrubbed. Called at startup after loading settings from DB.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Scrub the unformatted message string
        if isinstance(record.msg, str):
            record.msg = _scrub(record.msg)

        # Scrub format args (both tuple and dict forms)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _scrub(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _scrub(v) if isinstance(v, str) else v
                    for v in record.args
                )

        # Scrub exc_text if already populated (belt-and-suspenders;
        # usually None at filter time — use scrub_traceback() at call sites instead)
        if record.exc_text:
            record.exc_text = _scrub(record.exc_text)

        return True  # never suppress records
