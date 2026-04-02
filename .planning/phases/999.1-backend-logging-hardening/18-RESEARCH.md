# Phase 18: Backend Logging & Key Security Hardening - Research

**Researched:** 2026-04-01
**Domain:** Python logging filters, httpx event hooks, Fernet encryption, API key transmission
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**1. Masking format — LOG-02, SEC-01**
`***abc` format everywhere — last 3 characters of the actual key value, prefixed with `***`. Applied consistently across:
- Backend log statements
- Exception traceback strings before logging
- GET /settings API response (masked values returned, never full keys)
- Settings page display (already `type="password"` visually; backend now sends masked value)

**PUT /settings sentinel detection:** A value matches a masked sentinel if it starts with `***` and is ≤ 10 chars total. Do not save these.

**2. Encryption key — SEC-02**
Auto-generate and persist on first run. Never run with plaintext DB storage.
- Check `SETTINGS_ENCRYPTION_KEY` env var first
- If empty/missing, check `/app/data/.encryption_key` file
- If not found, generate new Fernet key, write to `/app/data/.encryption_key`
- If no key can be loaded or generated, app fails with clear error
- Docker volume at `/app/data/` already persists across container restarts

**3. GET /settings response masking — SEC-01**
Backend masks all key/credential fields before returning. Fields to mask:
- `tmdb_api_key`, `radarr_api_key`, `mdblist_api_key`
- Any future field whose DB name contains `key`, `token`, or `password`

**4. External API key transmission — SEC-03**
- TMDB: Upgrade from `?api_key=` to `Authorization: Bearer <token>` header
- MDBList: Leave as-is (query param only API) — accepted trade-off
- Radarr: Already uses `X-Api-Key` header — no change needed

**5. Log scrubbing scope — LOG-01**
Layer 1: Python `logging.Filter` on root logger scrubs known patterns from log messages.
Layer 2: httpx `event_hooks` on each `AsyncClient` instance redact headers and query params.
Exception tracebacks: `scrub_traceback(exc)` helper before passing to `logger.exception()`.

### Claude's Discretion

None specified.

### Deferred Ideas (OUT OF SCOPE)

- Frontend changes to Settings.tsx
- Per-request audit logging for settings reads/writes
- MDBList header auth
- HMAC request signing or CSP headers
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOG-01 | Scrub API key values from all log output (messages, httpx request URLs, exception tracebacks) | Logging filter pattern, httpx event hooks API, scrub_traceback helper |
| LOG-02 | Mask API key values in structured log messages with `***abc` format | mask_key() helper design, placement in settings_service.py |
| SEC-01 | GET /settings response never returns full key values; PUT /settings detects and skips masked sentinels | SettingsResponse masking before construction, sentinel detection pattern |
| SEC-02 | Encryption key auto-generated and persisted on first run; app never runs with plaintext DB storage | Fernet key bootstrap, atomic file write, lifespan ordering |
| SEC-03 | API keys transmitted via headers not URL query params where supported | TMDB Bearer token upgrade, TMDB credential distinction |
</phase_requirements>

---

## Summary

CinemaChain's backend currently logs API keys in plaintext — the TMDB key is embedded in every outgoing request URL as `?api_key=`, and exception tracebacks from httpx can capture the full URL with the key. The settings router returns full decrypted key values in GET /settings responses. Encryption is optional (silently skipped if no key configured).

This phase hardens all three attack surfaces: log output (filter + event hooks), API response exposure (masking before SettingsResponse construction), and key storage (mandatory Fernet encryption with auto-generate).

The most significant implementation decision uncovered during research is that TMDB's `api_key` (short hex string) and the "API Read Access Token" (long JWT-style token) are **two distinct credentials** from the TMDB account settings page. They are not interchangeable. The current codebase stores the v3 `api_key` — the Bearer upgrade requires storing and using the separate Read Access Token instead. This is a user-facing change (they must enter the Read Access Token, not the v3 API Key, after the upgrade).

**Primary recommendation:** All five research questions have clear, verifiable implementation paths. The TMDB credential distinction is the highest-risk item — the planner must document the credential change clearly so the user knows to update their stored TMDB key after deploying.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` (Fernet) | ≥42.0 (pinned in requirements.txt) | Symmetric encryption at rest | Already in use; Fernet is authenticated encryption with built-in IV |
| `httpx` | 0.27.2 (pinned) | HTTP client with event hooks | Already in use; event_hooks API is stable |
| `logging` (stdlib) | Python 3.11+ | Centralized log scrubbing via Filter | No additional dep; Filter installed on root logger |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` (stdlib) | — | Regex substitution in logging filter | Pattern-scrubbing fallback when exact key values are not loaded |
| `os` (stdlib) | — | Atomic temp-file write for encryption key | Already imported in main.py |

**No new dependencies required for this phase.**

---

## Architecture Patterns

### Recommended File Structure Changes

```
backend/app/
├── utils/
│   └── masking.py          # NEW: mask_key(), is_masked_sentinel(), scrub_text()
├── services/
│   └── settings_service.py # MODIFY: _get_fernet() mandatory; mask_key() imported from utils
├── routers/
│   └── settings.py         # MODIFY: apply masking before SettingsResponse; skip sentinels on PUT
├── main.py                  # MODIFY: encryption bootstrap before DB init; install root log filter
└── settings.py              # MODIFY: settings_encryption_key stays optional (auto-generate handles it)
```

### Q1: mask_key() Helper Placement

**Decision: `backend/app/utils/masking.py` (new file)**

Rationale: `mask_key()` is consumed by both `settings_service.py` (to mask before returning from `get_all_settings`) and `routers/settings.py` (to mask response). Putting it in `settings_service.py` would create a circular or awkward import if the router also needs it directly. A `utils/` module has no imports from `app.*` so it breaks no import cycles.

`is_masked_sentinel()` and `scrub_text()` (used by the log filter) also belong here — they are pure string utilities with no app dependencies.

```python
# backend/app/utils/__init__.py  — empty
# backend/app/utils/masking.py

import re

def mask_key(value: str | None) -> str | None:
    """Return ***abc (last 3 chars) format, or *** if value too short. None → None."""
    if value is None:
        return None
    if len(value) < 4:
        return "***"
    return "***" + value[-3:]

def is_masked_sentinel(value: str | None) -> bool:
    """True if value looks like a masked sentinel (starts with *** and ≤ 10 chars total)."""
    if not value:
        return False
    return value.startswith("***") and len(value) <= 10

def scrub_text(text: str, secrets: list[str]) -> str:
    """Replace all occurrences of each secret in text with [REDACTED]."""
    for secret in secrets:
        if secret and len(secret) >= 4:
            text = text.replace(secret, "[REDACTED]")
    return text
```

Import pattern in settings_service.py and routers/settings.py:
```python
from app.utils.masking import mask_key, is_masked_sentinel
```

### Q2: Logging Filter Implementation

**Decision: `logging.Filter` subclass installed on the root logger's handler(s)**

`logging.Filter` (not a custom `Formatter`) is the right tool because:
- Filters can modify records in-place (scrub `record.msg`, `record.args`, `record.exc_text`)
- Formatters are for output format only; scrubbing in a formatter leaves the record dirty in memory
- A single filter on the root logger's StreamHandler catches all log output regardless of which module emits it

**Where to install:** After `logging.basicConfig()` in `main.py`, before the lifespan function runs. The filter needs to be on the handler(s), not the logger itself — installing on a logger only affects records emitted *by that logger*, but handler-level filters apply to all records the handler receives.

**Circular import prevention:** The filter must not import from `app.services.settings_service` at module level (circular: main → settings_service → settings → main). Instead, use a mutable container (a list or a module-level dict) that main.py populates at startup after loading keys from DB.

```python
# backend/app/utils/masking.py (addition)

_active_secrets: list[str] = []

def register_secret(value: str) -> None:
    """Register a secret value for log scrubbing. Call at startup."""
    if value and value not in _active_secrets:
        _active_secrets.append(value)

def clear_secrets() -> None:
    """Clear registered secrets (for testing)."""
    _active_secrets.clear()
```

```python
# backend/app/utils/log_filter.py

import logging
import re
from app.utils.masking import _active_secrets, scrub_text

_PATTERN_SCRUBS = [
    # api_key / apikey query param — scrub the value portion
    (re.compile(r'(?i)(api_?key=)[A-Za-z0-9_\-]{8,}'), r'\1[REDACTED]'),
    # Authorization: Bearer header
    (re.compile(r'(?i)(Authorization:\s*Bearer\s+)\S+'), r'\1[REDACTED]'),
    # X-Api-Key header value
    (re.compile(r'(?i)(X-Api-Key[:\s]+)[A-Za-z0-9_\-]{8,}'), r'\1[REDACTED]'),
]

class ScrubSecretsFilter(logging.Filter):
    """Scrub known API key patterns and registered secret values from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Scrub the unformatted message
        if isinstance(record.msg, str):
            record.msg = self._scrub(record.msg)
        # Scrub string args
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._scrub(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._scrub(v) if isinstance(v, str) else v
                    for v in record.args
                )
        # Scrub cached exception text (set by Formatter on second pass, may be None here)
        if record.exc_text:
            record.exc_text = self._scrub(record.exc_text)
        return True

    def _scrub(self, text: str) -> str:
        for pattern, replacement in _PATTERN_SCRUBS:
            text = pattern.sub(replacement, text)
        return scrub_text(text, _active_secrets)
```

**How to install in main.py** (after `logging.basicConfig`):

```python
# main.py — top of file, after logging.basicConfig()
from app.utils.log_filter import ScrubSecretsFilter

_scrub_filter = ScrubSecretsFilter()
for handler in logging.getLogger().handlers:
    handler.addFilter(_scrub_filter)
```

**Injecting key values at startup** (in lifespan, after loading DB settings):

```python
from app.utils.masking import register_secret

# After loading settings from DB:
tmdb_key = await settings_service.get_setting(db, "tmdb_api_key")
radarr_key = await settings_service.get_setting(db, "radarr_api_key")
mdblist_key = await settings_service.get_setting(db, "mdblist_api_key")
for k in (tmdb_key, radarr_key, mdblist_key):
    if k:
        register_secret(k)
```

**Note on `record.exc_text`:** This attribute is set by the Formatter during `format()`, not during filter execution. The filter runs before format, so `exc_text` is usually `None` at filter time. To scrub exception tracebacks, use the `scrub_traceback()` helper (see Q3 / Common Pitfalls) before calling `logger.exception()`, rather than relying on the filter to catch `exc_text`.

### Q3: httpx Event Hooks for Request Scrubbing

**Exact hook signature for `httpx.AsyncClient`:**

```python
async def _scrub_request(request: httpx.Request) -> None:
    # Headers — httpx.Headers is immutable; must rebuild via update pattern
    # The request object passed to the hook is mutable via request.headers
    # but httpx.Headers does NOT support item assignment directly.
    # Use the workaround: copy and replace header values.
    sensitive_headers = {"authorization", "x-api-key"}
    for header_name in sensitive_headers:
        if header_name in request.headers:
            # Note: httpx.Request.headers is a MutableHeaders in 0.27.x
            request.headers[header_name] = "[REDACTED]"
    # Query params are in request.url — URL is immutable, log only
    # (The actual request is already sent; this hook fires after preparation,
    # before network send. You can log a scrubbed version but can't mutate URL.)
```

**CRITICAL: httpx event hooks fire AFTER the request is fully prepared but BEFORE it is sent.** This means:
- You CAN mutate `request.headers` (they are `MutableHeaders` in 0.27.x)
- You CANNOT mutate `request.url` — it is immutable after construction
- For TMDB: after switching to Bearer header, there is no key in the URL to scrub
- For MDBList: the `apikey` is in the query string. The hook can log a scrubbed URL for diagnostics but cannot redact the outgoing URL itself

**Registering on AsyncClient** (two methods — both work for class-level clients):

Method A — at construction (preferred for TMDBClient / RadarrClient which build client in `__init__`):

```python
# In TMDBClient.__init__:
self._client = httpx.AsyncClient(
    base_url=self.BASE_URL,
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=httpx.Timeout(connect=60.0, read=90.0, write=30.0, pool=10.0),
    event_hooks={"request": [_scrub_request_headers]},
)
```

Method B — via `.event_hooks` property (for MDBList which creates a local `async with` client per batch):

```python
async with httpx.AsyncClient(
    timeout=10.0,
    event_hooks={"request": [_scrub_request_headers]},
) as client:
    ...
```

**Compatibility with class-level `AsyncClient`:** Fully compatible in httpx 0.27.x. The `event_hooks` dict is stored on the client instance and fires on every request made through that instance.

**IMPORTANT:** For AsyncClient, hooks MUST be `async def` functions. A sync function registered as a hook on `AsyncClient` will raise a `TypeError` at hook execution time.

**Verified from httpx docs (0.27.x):** "If you are using HTTPX's async support, then hooks registered with `httpx.AsyncClient` MUST be async functions."

### Q4: Fernet Key Auto-Generation and Persistence

**Fernet key format:** A URL-safe base64-encoded 32-byte key. `Fernet.generate_key()` returns `bytes` of length 44.

```python
from cryptography.fernet import Fernet
key: bytes = Fernet.generate_key()
# key looks like: b'abc123...=' (44 chars, URL-safe base64)
# Store as string by decoding: key.decode()
```

**Atomic write pattern** (prevents partial writes if process dies mid-write):

```python
import os, pathlib, tempfile

KEY_FILE = pathlib.Path("/app/data/.encryption_key")

def _write_key_atomic(key_bytes: bytes) -> None:
    """Write key to file atomically using temp file + rename."""
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=KEY_FILE.parent, prefix=".enc_key_tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(key_bytes)
        os.chmod(tmp_path, 0o600)  # owner read/write only
        os.replace(tmp_path, KEY_FILE)  # atomic on POSIX
    except Exception:
        os.unlink(tmp_path)
        raise
```

**Bootstrap function for lifespan** (goes in `settings_service.py` or a new `app/crypto.py`):

```python
def bootstrap_encryption_key() -> None:
    """
    Load or generate the Fernet encryption key.
    Priority: SETTINGS_ENCRYPTION_KEY env var → /app/data/.encryption_key file → generate new.
    Updates env_settings in-place so _get_fernet() picks it up immediately.
    Raises RuntimeError if key cannot be established.
    """
    from app.settings import settings as env_settings

    # 1. Env var (set by user or Docker secret)
    if env_settings.settings_encryption_key:
        # Validate it's a real Fernet key
        try:
            Fernet(env_settings.settings_encryption_key.encode())
            logger.info("Encryption key loaded from SETTINGS_ENCRYPTION_KEY env var")
            return
        except Exception as exc:
            raise RuntimeError(f"SETTINGS_ENCRYPTION_KEY is set but invalid: {exc}") from exc

    # 2. Persisted key file on Docker volume
    key_file = pathlib.Path("/app/data/.encryption_key")
    if key_file.exists():
        try:
            key_bytes = key_file.read_bytes().strip()
            Fernet(key_bytes)  # validate
            env_settings.settings_encryption_key = key_bytes.decode()
            logger.info("Encryption key loaded from %s", key_file)
            return
        except Exception as exc:
            raise RuntimeError(f"Key file {key_file} exists but is invalid: {exc}") from exc

    # 3. Generate and persist
    new_key = Fernet.generate_key()
    _write_key_atomic(new_key)
    env_settings.settings_encryption_key = new_key.decode()
    logger.info("Generated new Fernet encryption key → %s", key_file)
```

**Ordering in lifespan:** Bootstrap BEFORE DB init and BEFORE `migrate_env_to_db`. If DB init runs first and `migrate_env_to_db` tries to encrypt, `_get_fernet()` returns None and values are stored plaintext. Correct order:

```
1. bootstrap_encryption_key()        ← NEW, first
2. DB connection verify
3. migrate_env_to_db()               ← now has Fernet available
4. Load DB settings / init clients
5. register_secret() for log filter
```

**Note on pydantic-settings:** `env_settings` is a pydantic `Settings` instance which is normally immutable. To mutate `settings_encryption_key` after construction, either use `model_config = {"frozen": False}` (already default for BaseSettings) or assign directly. Pydantic BaseSettings does not set `model_config["frozen"] = True` by default, so `env_settings.settings_encryption_key = ...` works.

### Q5: Re-Encryption of Existing Plaintext DB Values

**Code path trace:**

1. `bootstrap_encryption_key()` runs first — sets `env_settings.settings_encryption_key` to a valid key
2. `migrate_env_to_db(db)` runs — but only if `app_settings` table is **empty**
3. If table already has rows (existing deployment), migration is skipped entirely
4. Existing plaintext values in DB are NOT automatically re-encrypted

**The gap identified:** The CONTEXT.md says "Re-encryption of any existing plaintext values in DB should happen silently on first startup when a key is generated." This is NOT what the current code does. `migrate_env_to_db` only runs on an empty table. Existing plaintext rows will remain plaintext until explicitly re-saved.

**Required addition:** A `re_encrypt_plaintext_settings(db)` pass that:
- Reads all rows where `is_secret = True`
- Attempts `decrypt_value(row.value)` — if Fernet returns the same string (InvalidToken caught → returns raw), the value is plaintext
- Re-encrypts with the current key and saves back

```python
async def re_encrypt_plaintext_settings(db: AsyncSession) -> int:
    """
    Re-encrypt any settings rows that are marked is_secret but stored as plaintext.
    Returns count of rows re-encrypted. Safe to call on already-encrypted rows (no-op).
    """
    result = await db.execute(
        select(AppSettings).where(AppSettings.is_secret == True)  # noqa: E712
    )
    rows = result.scalars().all()
    fernet = _get_fernet()
    if fernet is None:
        return 0

    count = 0
    for row in rows:
        if row.value is None:
            continue
        # Try to decrypt — if it fails (InvalidToken), it's plaintext
        try:
            fernet.decrypt(row.value.encode())
            # Already encrypted — skip
        except Exception:
            # It's plaintext — encrypt it
            row.value = encrypt_value(row.value)
            count += 1

    if count:
        logger.info("Re-encrypted %d plaintext secret settings rows", count)
    return count
```

Call in lifespan after `migrate_env_to_db` and `db.commit()`.

### Q6: TMDB Bearer Token — CRITICAL CREDENTIAL DISTINCTION

**Finding: TMDB `api_key` and "API Read Access Token" are TWO DIFFERENT CREDENTIALS.**

From TMDB account settings page, users see two distinct values:
- **API Key (v3 auth):** Short hex string, ~32 chars (e.g., `abc123def456...`)
- **API Read Access Token (v4 auth):** Long JWT-style token, ~200+ chars starting with `eyJ...`

These are NOT the same value used in different ways. They are separate credentials derived from the same account but with different formats and different storage.

**Implication for this phase:** Upgrading TMDBClient to use `Authorization: Bearer` requires the user to store their **Read Access Token** in settings, not their v3 API Key. The current `tmdb_api_key` field holds the v3 key. After the upgrade:

Option A — add a new `tmdb_read_access_token` field and keep `tmdb_api_key` for the v3 key
Option B — repurpose `tmdb_api_key` to store the Read Access Token (breaking: users must re-enter)

**Recommendation based on codebase:** The `tmdb_api_key` field is used in one place at startup (`settings.tmdb_api_key` in lifespan → `TMDBClient(api_key=...)`). The simplest path is Option B: repurpose the field, add a comment in Settings UI that the field now expects the "API Read Access Token (v4 auth)" not the "API Key". This requires the user to update their stored value after deploying.

**If the user currently has a v3 API key stored:** The Bearer token upgrade will break authentication until they enter the Read Access Token. The planner must create a task that documents this user action.

**TMDB v3 endpoints and Bearer token:** ALL v3 endpoints support Bearer token authentication — including `/movie/{id}`, `/person/{id}`, `/discover/movie`, `/search/person`. No v3 endpoints require `api_key` query param exclusively. Source: TMDB developer docs (developer.themoviedb.org/docs/authentication-application).

**Exact header format:**
```
Authorization: Bearer <read_access_token>
```

**TMDBClient `__init__` change:**
```python
def __init__(self, api_key: str) -> None:
    # api_key parameter name kept for backward compat; value is now Read Access Token
    self._client = httpx.AsyncClient(
        base_url=self.BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=httpx.Timeout(connect=60.0, read=90.0, write=30.0, pool=10.0),
    )
```

Note: Remove `params={"api_key": api_key}` — do NOT pass both. The key is no longer needed as a query param.

### Q7: PUT /settings Sentinel Detection

**Pattern:** `value.startswith("***") and len(value) <= 10`

**Real key minimum lengths (verified):**
- TMDB v3 API Key: 32 hex characters (always exactly 32)
- TMDB Read Access Token: 200+ characters (JWT format)
- Radarr API Key: 32 alphanumeric characters (UUID format without hyphens)
- MDBList API Key: 16–32 alphanumeric characters (varies by account tier)

**Safety analysis:** A real key cannot be ≤ 10 chars AND start with `***`. The shortest real key (MDBList minimum ~16 chars) is well above the 10-char threshold. The `***` prefix is also not a valid start for any of these key formats (hex, JWT, UUID-style).

**The sentinel values the backend will send:**
- `***abc` = 6 chars — matches sentinel
- `***` = 3 chars — matches sentinel (empty key stored)
- Real key `abcde12345` = 10 chars, does NOT start with `***` — not a sentinel

**Confirmed safe** — no collision risk.

**Implementation in `routers/settings.py` PUT handler:**

```python
from app.utils.masking import is_masked_sentinel, mask_key

@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Save updated settings. Skips masked sentinel values (user did not change the field)."""
    updates = {
        k: v
        for k, v in body.model_dump(exclude_none=True).items()
        if not is_masked_sentinel(v)
    }
    if updates:
        await settings_service.save_settings(db, updates)
        await db.commit()
    data = await settings_service.get_all_settings(db)
    # Mask secrets before returning
    masked = _mask_settings_response(data)
    return SettingsResponse(**{k: masked.get(k) for k in SettingsResponse.model_fields})
```

### Q8: SettingsResponse vs SettingsDTO — Masking Location

**Current architecture:** There is ONE model: `SettingsResponse` in `routers/settings.py`. No separate internal DTO. `get_all_settings()` returns a raw `dict[str, str | None]` with decrypted values. The router constructs `SettingsResponse` directly from that dict.

**Where masking MUST happen:** Before `SettingsResponse(...)` is constructed. The masking logic belongs in the router, not in `get_all_settings()` — because `get_all_settings()` is also called internally (e.g., to load keys for TMDBClient). If masking were in `get_all_settings()`, internal callers would receive masked values and break.

**Pattern:**

```python
# In routers/settings.py

_SECRET_FIELDS = {"tmdb_api_key", "radarr_api_key", "mdblist_api_key"}

def _mask_settings_response(data: dict[str, str | None]) -> dict[str, str | None]:
    """Apply mask_key() to all secret fields before building SettingsResponse."""
    result = dict(data)
    for field in _SECRET_FIELDS:
        if field in result:
            result[field] = mask_key(result[field])
    return result
```

**GET /settings handler becomes:**

```python
@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    """Return all current settings with secret fields masked."""
    data = await settings_service.get_all_settings(db)
    masked = _mask_settings_response(data)
    return SettingsResponse(**{k: masked.get(k) for k in SettingsResponse.model_fields})
```

**No changes needed to `SettingsResponse` model itself** — it stays as-is, but now receives masked values. No new DTO required.

**Exception: internal callers of `get_all_settings()`** — only the router returns responses to clients, so masking only at the router boundary is correct. `settings_service.get_all_settings()` continues to return full decrypted values for internal use.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Authenticated symmetric encryption | Custom AES wrapper | `cryptography.Fernet` | Fernet handles IV, HMAC, key derivation correctly; rolling crypto is error-prone |
| Log record scrubbing | String replace in every logger.info() call | `logging.Filter` on root handler | Centralized; catches third-party library log output too |
| Atomic file writes | Direct `open(path, 'w').write()` | `tempfile.mkstemp` + `os.replace()` | `os.replace()` is atomic on POSIX; direct write risks corrupt file if process dies |
| httpx request scrubbing per-call | Manual logging before each `client.get()` | `event_hooks={"request": [...]}` | Hooks fire automatically; no risk of forgetting on new call sites |

---

## Common Pitfalls

### Pitfall 1: Scrubbing exc_text in the logging filter
**What goes wrong:** `record.exc_text` is `None` at filter time. It is set by `logging.Formatter.format()`, which runs after the filter. Attempting to scrub `record.exc_text` in the filter will find it empty and do nothing. The traceback appears in logs unredacted.
**Why it happens:** Python logging pipeline order: emit() → filter() → format() → handler output. `exc_text` is only populated during format().
**How to avoid:** Use a `scrub_traceback(exc)` helper at call sites before logging, OR install the filter on the handler and also override `Formatter.formatException()` to scrub the exception string. The simpler approach is the call-site helper:
```python
def scrub_traceback(text: str) -> str:
    return scrub_text(text, _active_secrets)

# Usage:
try:
    ...
except Exception as exc:
    safe_tb = scrub_traceback(traceback.format_exc())
    logger.error("Failed: %s\n%s", context_msg, safe_tb)
    # Do NOT use logger.exception() here — that would bypass scrubbing
```

### Pitfall 2: httpx event hooks must be async for AsyncClient
**What goes wrong:** Registering a sync function as a hook on `httpx.AsyncClient` raises `TypeError: object bool can't be used in 'await' expression` at runtime, not at registration time.
**Why it happens:** httpx checks at hook-call time, not at registration time. The error only surfaces on the first real request.
**How to avoid:** Always declare hook functions with `async def`. Add a test that exercises one request through the patched client.

### Pitfall 3: Mutating pydantic Settings at startup
**What goes wrong:** `env_settings.settings_encryption_key = new_key.decode()` raises `ValidationError` or `TypeError` if `Settings` uses `model_config = {"frozen": True}`.
**Why it happens:** pydantic v2's BaseSettings does not freeze by default, but it's easy to accidentally set `frozen=True`.
**How to avoid:** Verify `settings.py` does not set `frozen=True` (it currently does not). Alternatively, use `object.__setattr__(env_settings, "settings_encryption_key", new_key.decode())` which bypasses pydantic validation entirely as a safe escape hatch.

### Pitfall 4: TMDB v3 API Key used as Bearer token value
**What goes wrong:** Switching TMDBClient to `Authorization: Bearer <tmdb_api_key>` where `tmdb_api_key` contains the v3 API Key (short hex string) will result in 401 responses from TMDB.
**Why it happens:** TMDB validates Bearer tokens as JWT-format Read Access Tokens, not v3 API Keys. The two credential types are structurally different and are not interchangeable.
**How to avoid:** The planner must create a task documenting that the user needs to obtain their "API Read Access Token" (long JWT) from their TMDB account API settings page and update it in CinemaChain settings after deploying this phase.

### Pitfall 5: Log filter not installed on handlers added after basicConfig
**What goes wrong:** If a library or middleware adds a new handler to the root logger after the scrub filter is installed, that handler will NOT have the filter.
**Why it happens:** `addFilter()` attaches to a specific handler instance; new handlers have no filters.
**How to avoid:** Install the filter on the root logger itself (not just its handlers), OR use a subclass of `logging.StreamHandler` that always applies scrubbing. Installing on the root logger (via `logging.getLogger().addFilter(scrub_filter)`) ensures it runs for all records before any handler sees them.
```python
# Preferred: install on root logger, not handlers
logging.getLogger().addFilter(_scrub_filter)
```
Note: Installing on the root *logger* (not its handlers) means the filter runs before records propagate to handlers. Records from child loggers DO propagate to the root logger's filters. This is the safest installation point.

### Pitfall 6: re_encrypt_plaintext_settings requires a DB commit
**What goes wrong:** Calling `re_encrypt_plaintext_settings(db)` modifies SQLAlchemy ORM objects in the session but the caller forgets to `await db.commit()` after.
**Why it happens:** SQLAlchemy async sessions are not auto-commit.
**How to avoid:** Have `re_encrypt_plaintext_settings` call `await db.flush()` internally so changes are staged, and document that the caller must commit. Or have it commit internally and document that behavior.

---

## Code Examples

### mask_key() — canonical implementation
```python
# Source: CONTEXT.md decision + implementation design
def mask_key(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) < 4:
        return "***"
    return "***" + value[-3:]
```

### Fernet key bootstrap (lifespan-safe)
```python
# Source: cryptography.fernet docs + os.replace atomic pattern
from cryptography.fernet import Fernet
import pathlib, os, tempfile

KEY_FILE = pathlib.Path("/app/data/.encryption_key")

def bootstrap_encryption_key() -> None:
    from app.settings import settings as env_settings
    if env_settings.settings_encryption_key:
        Fernet(env_settings.settings_encryption_key.encode())  # validate
        return
    if KEY_FILE.exists():
        key_bytes = KEY_FILE.read_bytes().strip()
        Fernet(key_bytes)  # validate
        env_settings.settings_encryption_key = key_bytes.decode()
        return
    new_key = Fernet.generate_key()
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=KEY_FILE.parent, prefix=".enc_key_tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(new_key)
        os.chmod(tmp, 0o600)
        os.replace(tmp, KEY_FILE)
    except Exception:
        os.unlink(tmp)
        raise
    env_settings.settings_encryption_key = new_key.decode()
```

### httpx async event hook — header scrubbing
```python
# Source: httpx 0.27.x docs (python-httpx.org/advanced/event-hooks/)
import httpx

async def _scrub_auth_headers(request: httpx.Request) -> None:
    """Redact auth headers from the request object (for logging hooks)."""
    for name in ("authorization", "x-api-key"):
        if name in request.headers:
            request.headers[name] = "[REDACTED]"

# Registration at AsyncClient construction:
client = httpx.AsyncClient(
    event_hooks={"request": [_scrub_auth_headers]}
)
```

### ScrubSecretsFilter — installing on root logger
```python
# Source: Python logging docs (docs.python.org/3/library/logging.html)
import logging

scrub_filter = ScrubSecretsFilter()
logging.getLogger().addFilter(scrub_filter)
# Install AFTER logging.basicConfig(), BEFORE lifespan starts
```

### GET /settings — masking before response
```python
# Source: routers/settings.py analysis

_SECRET_FIELDS = {"tmdb_api_key", "radarr_api_key", "mdblist_api_key"}

@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    data = await settings_service.get_all_settings(db)
    for field in _SECRET_FIELDS:
        if field in data:
            data[field] = mask_key(data[field])
    return SettingsResponse(**{k: data.get(k) for k in SettingsResponse.model_fields})
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| Config file | `backend/pytest.ini` or `backend/pyproject.toml` (check at run time) |
| Quick run command | `cd backend && pytest tests/test_settings.py tests/test_tmdb.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOG-01 | Logging filter scrubs key values from log output | unit | `pytest tests/test_logging_filter.py -x` | ❌ Wave 0 |
| LOG-01 | httpx event hook redacts Authorization header | unit | `pytest tests/test_logging_filter.py::test_event_hook_scrubs_header -x` | ❌ Wave 0 |
| LOG-02 | mask_key() returns `***abc` format correctly | unit | `pytest tests/test_masking.py -x` | ❌ Wave 0 |
| LOG-02 | mask_key(None) returns None; mask_key short value returns `***` | unit | `pytest tests/test_masking.py::test_mask_key_edge_cases -x` | ❌ Wave 0 |
| SEC-01 | GET /settings response masks tmdb_api_key, radarr_api_key, mdblist_api_key | integration | `pytest tests/test_settings.py::test_get_settings_masks_keys -x` | ❌ Wave 0 |
| SEC-01 | PUT /settings with masked sentinel does not overwrite stored key | integration | `pytest tests/test_settings.py::test_put_settings_skips_sentinel -x` | ❌ Wave 0 |
| SEC-02 | bootstrap_encryption_key generates key file when none exists | unit | `pytest tests/test_encryption.py::test_bootstrap_generates_key -x` | ❌ Wave 0 |
| SEC-02 | bootstrap_encryption_key loads from env var | unit | `pytest tests/test_encryption.py::test_bootstrap_uses_env_var -x` | ❌ Wave 0 |
| SEC-02 | re_encrypt_plaintext_settings re-encrypts plaintext rows | unit | `pytest tests/test_encryption.py::test_reencrypt_plaintext -x` | ❌ Wave 0 |
| SEC-03 | TMDBClient sends Authorization: Bearer header, not api_key param | unit | `pytest tests/test_tmdb.py::test_tmdb_uses_bearer_header -x` | ❌ Wave 0 (existing test_tmdb.py needs new test) |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_masking.py tests/test_encryption.py tests/test_logging_filter.py -x -q`
- **Per wave merge:** `cd backend && pytest tests/test_settings.py tests/test_tmdb.py tests/test_masking.py tests/test_encryption.py tests/test_logging_filter.py -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_masking.py` — covers LOG-02, SEC-01 (mask_key, is_masked_sentinel)
- [ ] `backend/tests/test_encryption.py` — covers SEC-02 (bootstrap, re-encrypt, atomic write)
- [ ] `backend/tests/test_logging_filter.py` — covers LOG-01 (ScrubSecretsFilter, event hooks)
- [ ] `backend/app/utils/__init__.py` — empty init for utils package
- [ ] `backend/app/utils/masking.py` — new file (mask_key, is_masked_sentinel, scrub_text, register_secret)
- [ ] `backend/app/utils/log_filter.py` — new file (ScrubSecretsFilter)
- [ ] Extend `backend/tests/test_settings.py` with SEC-01 masking tests

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TMDB `?api_key=` query param | `Authorization: Bearer` header | TMDB docs updated ~2022; both still supported | Key no longer in URLs or httpx request logs |
| Optional Fernet encryption (silent skip) | Mandatory encryption with auto-generate | This phase | App will fail hard if key bootstrap fails — no silent plaintext fallback |
| `logging.basicConfig` only | + `ScrubSecretsFilter` on root logger | This phase | Third-party library log lines also scrubbed |

**Deprecated/outdated patterns being removed:**
- `_get_fernet() → None` path: the "return plaintext silently if no key" behavior in `encrypt_value()` and `decrypt_value()` should be hardened to raise after bootstrap, not silently degrade

---

## Open Questions

1. **TMDB Read Access Token stored in existing `tmdb_api_key` DB field**
   - What we know: Upgrade requires the Read Access Token (JWT, ~200 chars), not the v3 API Key
   - What's unclear: The `AppSettings` table stores values in a `TEXT` column — no length constraint issue. But the `settings.py` pydantic model uses `tmdb_api_key: str` which is also fine.
   - Recommendation: Planner must include a task that communicates to the user: "After deploying Phase 18, open Settings, clear the TMDB API Key field, and enter your TMDB API Read Access Token (found on your TMDB account API settings page, not the API Key)." Mark this as a required manual step.

2. **Log filter and uvicorn's access log**
   - What we know: uvicorn's access log is a separate logger (`uvicorn.access`) that logs request URLs including query strings. If TMDB still uses query params anywhere, those URLs appear in uvicorn access logs.
   - What's unclear: After Bearer upgrade, TMDB has no key in URLs. MDBList still has `apikey=` in outgoing request URLs, but these are client-side requests, not incoming requests to the CinemaChain server — so uvicorn access logs won't capture them.
   - Recommendation: No action needed for uvicorn access logs after TMDB Bearer upgrade. MDBList's `apikey=` is only in outgoing httpx requests, not in uvicorn's incoming access log.

3. **`test_db_overrides_env` in test_settings.py will break after masking**
   - What we know: Line 73 asserts `resp2.json()["tmdb_api_key"] == "new_test_key_override"`. After this phase, the response returns `***ide` (masked).
   - Recommendation: Planner must include a task to update this existing test assertion to check for masked format.

---

## Sources

### Primary (HIGH confidence)
- Python docs `logging.Filter` — https://docs.python.org/3/library/logging.html#filter-objects — filter(), LogRecord attributes, installation on logger vs handler
- httpx docs event-hooks — https://www.python-httpx.org/advanced/event-hooks/ — async hook requirement, registration API, hook signatures
- TMDB developer docs authentication — https://developer.themoviedb.org/docs/authentication-application — Bearer token format, v3 endpoint compatibility
- cryptography.fernet — cryptography≥42 pinned in requirements.txt — Fernet.generate_key(), Fernet() constructor, InvalidToken

### Secondary (MEDIUM confidence)
- TMDB community forum — https://www.themoviedb.org/talk/67abc733d669bf0eaa9b7dbb — confirmation that api_key and Read Access Token are distinct credentials
- TMDB community forum — https://www.themoviedb.org/talk/65c75581aad9c2017db69948 — v3 vs v4 token scope clarification

### Tertiary (LOW confidence)
- None — all critical claims verified against PRIMARY sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt, versions confirmed
- Architecture (logging filter, event hooks): HIGH — verified against Python docs and httpx docs
- TMDB Bearer/API-key distinction: HIGH — verified against official TMDB developer docs + two community confirmations
- Re-encryption gap (Q5): HIGH — traced directly from settings_service.py source code
- Pitfalls: HIGH — derived from source code inspection + official docs

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable domain — httpx, cryptography, Python logging all stable APIs)
