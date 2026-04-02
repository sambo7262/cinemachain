# Phase 21 Context: Pre-Deploy Hardening — API Key Validation & Git Cleanup

**Phase goal:** Add test-connection buttons for all three API keys in Settings, and clean up the git repository before v2.0 is tagged and published.

**Requirements:** (to be formalised in plan) — API key validation UX, git history squash, .env.example cleanup

---

## Decision 1 — Test button placement & UX

**Decision:** One test button per service card (TMDB card, MDBList card, Radarr card). No single "Test All" button.

**Button states:**
- Default: neutral / outline (same style as existing action buttons)
- Testing: disabled + spinner / "Testing..."
- Success: green with a short success message (e.g. "Connected")
- Failure: red with a verbose, specific error message inline under the button

**Auto-test on save:** When the user hits Save Settings, run validation for all services whose keys are present, in addition to saving. Validation result is shown per-card after save completes.

**Masked key behaviour:** If the user has not changed a key (frontend holds the `***abc` sentinel), the test button should validate using the **stored DB key** — not block with "save a new key first". The backend test endpoint decrypts and uses the live stored value.

---

## Decision 2 — Radarr test scope & error granularity

**Decision:** Test all three Radarr settings in sequence:
1. URL reachable (HTTP connection to `{radarr_url}/api/v3/system/status`)
2. API key accepted (same call — 401 = key invalid)
3. Quality profile exists (`/api/v3/qualityprofile` → name match)

**Failure vs warning:**
- Steps 1 & 2 failure → red / hard failure (Radarr is unusable)
- Step 3 mismatch → **yellow warning** (e.g. "Quality profile 'HD+' not found — will fall back to first available profile")

**Save blocking:** None. Radarr test failure/warning never blocks the save action.

**Error messages:** Verbose and specific:
- "Cannot reach Radarr at http://... — check the URL and that Radarr is running"
- "Radarr rejected the API key — check Settings > General > Security in Radarr"
- "Quality profile 'HD+' not found — available profiles: [X, Y, Z]"

---

## Decision 3 — MDBList test scope

**Decision:** Single call to a lightweight MDBList endpoint to verify the key is valid. Use a non-destructive endpoint that doesn't consume meaningful daily quota (e.g. user info or a single-movie lookup with a known TMDB ID).

**MDBList is optional** — its card already shows "Optional" in the description. Test failure = red state but not a save blocker and not shown as critical.

---

## Decision 4 — Backend validation endpoints

**Decision:** Add a new `POST /settings/validate` endpoint (or `POST /settings/validate/{service}` per-service). The endpoint:
- Reads the stored (decrypted) key from DB for any field submitted as a masked sentinel
- Uses a real key if the user submitted a plaintext value (live test before save)
- Returns per-service result: `{ "tmdb": {"ok": true}, "radarr": {"ok": false, "error": "..."}, "mdblist": {"ok": true, "warning": "..."} }`

The frontend calls this endpoint on explicit button click (per-card) and also after save completes (all services).

---

## Decision 5 — Git history cleanup

**Target history after cleanup:**
```
71b6b0b  ← v1.0 tag (unchanged — kept as parent)
<new>    ← v2.0 tag + latest tag  (all v2 commits squashed into one)
```

**Mechanism:**
1. `git reset --soft v1.0` — stages all v2 changes without touching working tree
2. `git commit -m "feat: CinemaChain v2.0"` — single squash commit
3. `git push --force origin main`
4. `git tag -d v1.0 && git push origin :refs/tags/v1.0` — re-push v1.0 tag if needed (it already points to the right commit)
5. `git tag v2.0 && git tag latest && git push origin v2.0 latest`

**This is destructive and irreversible on the remote.** Solo project — no collaborators. Confirmed acceptable.

---

## Decision 6 — .env.example cleanup

**Files to update:**

`backend/.env.example` — delete orphaned fields: `PLEX_TOKEN`, `PLEX_URL`, `SONARR_URL`, `SONARR_API_KEY`, `TS_AUTHKEY`. These have never been supported in v2 and are dead. Also align with the current Settings model (drop any v1-only vars).

`SETTINGS_ENCRYPTION_KEY` comment in root `.env.example` — update to reflect Phase 18 reality: the key is **auto-generated and persisted** on first run. Users do not need to set this. Update comment to say so (or remove the variable from `.env.example` entirely).

Root `.env.example` — already clean structure; only update the `SETTINGS_ENCRYPTION_KEY` comment.

---

## Code context

| File | Concern |
|------|---------|
| `frontend/src/pages/Settings.tsx` | Add test button per card; wire to validate endpoint; show green/red/yellow state |
| `backend/app/routers/settings.py` | Add `POST /settings/validate` endpoint; decrypt stored keys for masked inputs |
| `backend/app/services/tmdb.py` | Add `async def test_connection() -> None` — hits `/configuration` or `/authentication` |
| `backend/app/services/radarr.py` | Add `async def test_connection()` — URL ping → key check → profile check; returns structured result |
| `backend/app/services/mdblist.py` | Add `async def test_connection()` — lightweight key validation call |
| `backend/.env.example` | Remove Plex, Sonarr, Tailscale fields |
| `.env.example` (root) | Update `SETTINGS_ENCRYPTION_KEY` comment |

---

## Deferred / out of scope

- Validation on first onboarding (the onboarding gate already blocks on TMDB key presence — live validation there is a separate UX concern)
- Per-field validation on keystroke / blur (too noisy; explicit test button is sufficient)
- Docker Hub publish automation — out of scope for this phase
