# Phase 18 Context: Backend Logging & Key Security Hardening

**Phase goal:** Scrub API keys from all backend logs and exception tracebacks; harden key storage, transmission, and API response exposure so keys cannot be extracted once saved.

**Requirements:** LOG-01, LOG-02, SEC-01, SEC-02, SEC-03

---

## Decisions

### 1. Masking format — LOG-02, SEC-01

**Decision:** `***abc` format everywhere — last 3 characters of the actual key value, prefixed with `***`. Applied consistently across:
- Backend log statements
- Exception traceback strings before logging
- GET /settings API response (masked values returned, never full keys)
- Settings page display (already `type="password"` visually; backend now sends masked value)

**Implication for PUT /settings:** When a user submits settings without changing a key field, the frontend will submit the masked value (e.g. `***abc`). The backend must detect this pattern and treat it as "no change" — skip overwriting the stored key. Only write to DB when the submitted value is a real new key (not a masked sentinel).

**Pattern for detection:** A value matches a masked sentinel if it starts with `***` and is ≤ 10 chars total. Do not save these.

---

### 2. Encryption key — SEC-02

**Decision:** Auto-generate and persist on first run. Never run with plaintext DB storage.

**Mechanism:**
- On app startup, check `SETTINGS_ENCRYPTION_KEY` env var
- If empty/missing, check for `/app/data/.encryption_key` file (on the persisted Docker volume)
- If not found, generate a new Fernet key, write to `/app/data/.encryption_key`
- Load whichever was found and use it as the active key
- Remove the optional fallback — if no key can be loaded or generated, app fails with a clear error

**Why file-based persistence:** Docker volume at `/app/data/` already persists across container restarts on the NAS. This avoids requiring manual user setup while surviving container rebuilds.

**Existing encrypted values:** Re-encryption of any existing plaintext values in DB should happen silently on first startup when a key is generated. The `_migrate_env_keys` flow already reads and re-saves — the encrypt path will apply automatically.

---

### 3. GET /settings response masking — SEC-01

**Decision:** Backend masks all key/credential fields before returning in API response. Frontend never receives a full key value after the initial save request completes.

**Fields to mask in SettingsResponse / SettingsDTO:**
- `tmdb_api_key`
- `radarr_api_key`
- `mdblist_api_key`
- Any future field whose DB name contains `key`, `token`, or `password`

**Masking logic:** Apply `mask_key(value)` helper — returns `***` + last 3 chars, or `***` if value is shorter than 4 chars or empty/None.

**PUT /settings response:** Also returns masked values (same logic — response after save shows `***abc`, not the full key just submitted).

**Settings page UX:** No frontend changes needed. The input fields already use `type="password"`. The masked value `***abc` in the field tells the user a key is saved. To update, they clear the field and type a new value — the backend sees a non-masked value and saves it.

---

### 4. External API key transmission — SEC-03

**Decision:** HTTP headers preferred over URL query params. Upgrade where supported; best-effort for others.

**TMDB:** Upgrade from `?api_key=` query param to `Authorization: Bearer <token>` header. TMDB v3 supports both; the `api_key` param is the legacy path. The existing `tmdb_api_key` field is used as the Bearer token value (TMDB uses the same key for both auth methods). Update `TMDBClient.__init__` to set `Authorization` header instead of default params.

**MDBList:** MDBList API only supports `?apikey=` query param — no header auth option available. Leave as-is. The key is still protected by DB encryption and masked in GET /settings; the query param exposure is an accepted trade-off for a NAS-local app.

**Radarr:** Already uses `X-Api-Key` header. No change needed.

**Scope note:** The concern here is primarily about keys appearing in httpx request logs and local access logs. Fixing TMDB removes the most common case (TMDB is called on every cache job). MDBList is lower frequency.

---

### 5. Log scrubbing scope — LOG-01

**Decision:** Scrub keys from logs at two layers:

**Layer 1 — Logging filter (centralized):**
Install a Python `logging.Filter` on the root logger that regex-replaces any known sensitive patterns in log messages before they're written. Patterns to scrub:
- Long alphanumeric strings that appear after `api_key=`, `apikey=`, `Authorization: Bearer `, `key=`
- The actual key values themselves (injected dynamically from loaded settings at startup)

**Layer 2 — httpx event hooks:**
Add `event_hooks` to each `httpx.AsyncClient` instance to redact `Authorization` and `X-Api-Key` headers from request logs, and scrub `api_key`/`apikey` query params from logged URLs.

**Exception tracebacks:** Wrap logging of caught exceptions with a `scrub_traceback(exc)` helper that replaces known key values in the exception string and `__cause__`/`__context__` chains before passing to `logger.exception()`.

**Not in scope:** httpx DEBUG-level logs for request/response bodies — these are off by default and not enabled in this app.

---

## Code context

| File | Concern |
|------|---------|
| `backend/app/services/settings_service.py` | Encryption: optional → mandatory; add auto-generate logic; add `mask_key()` helper |
| `backend/app/routers/settings.py` | GET /settings: apply masking before return; PUT /settings: skip masked sentinel values on write |
| `backend/app/services/tmdb.py` | Replace `params={"api_key": ...}` with `headers={"Authorization": "Bearer ..."}` |
| `backend/app/services/mdblist.py` | Leave query params; add httpx event hook to scrub from logs |
| `backend/app/services/radarr.py` | Already uses `X-Api-Key` header; add event hook to scrub from logs |
| `backend/app/main.py` | Install root logging filter; bootstrap encryption key at startup |
| `backend/app/settings.py` | `settings_encryption_key` no longer optional — handled by auto-generate, not by making it required in pydantic |

---

## Deferred / out of scope

- Frontend changes to Settings.tsx: no changes needed — masked values from backend work with existing `type="password"` fields
- Per-request audit logging for settings reads/writes: deferred to a future hardening pass
- MDBList header auth: not supported by MDBList API
- HMAC request signing or CSP headers: out of scope for a NAS-local app
