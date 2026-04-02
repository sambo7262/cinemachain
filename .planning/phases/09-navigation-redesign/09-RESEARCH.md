# Phase 9: Navigation Redesign — Research

**Researched:** 2026-03-30
**Domain:** React Router v7 (legacy BrowserRouter mode), shadcn Tabs, React component refactor
**Confidence:** HIGH — all findings verified directly against the codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Three permanent nav items: **Game Mode**, **Search**, **Settings**
- "Search" is the label (not "Query Mode")
- Settings remains icon-only (gear icon, existing treatment)
- Active state highlight on the current section, same pattern as today
- Game Mode routes to `/game` (lobby moves from `/` to `/game`)
- No redirect from `/` to `/game` — just remove the `/` route and set `/game` as canonical
- Lobby page content and appearance unchanged
- `/archived` route removed entirely (no redirect needed)
- Archived sessions surface as **Active | Archived** tabs within Game Mode page
- Default tab on landing: **Active** (not persisted)
- `/search` route renders a placeholder: dark card, "Search" heading + "Coming soon.", no back button

### Claude's Discretion
- None noted — all structural decisions are locked

### Deferred Ideas (OUT OF SCOPE)
- Actual Search / Query Mode functionality (Phase 10+)
- Any changes to game session behaviour
</user_constraints>

---

## Summary

This is a small, self-contained frontend refactor with four distinct changes: (1) reroute the lobby from `/` to `/game`, (2) add `/search` placeholder, (3) merge ArchivedSessions as a tab inside GameLobby, and (4) update NavBar active-state logic.

The app runs React Router v7.13.1 in legacy `BrowserRouter` + `<Routes>` mode — the same declarative `<Route>` API as RR v6. There is no data-router, no loader/action, no file-based routing. The upgrade from v6 to v7 in this mode is a no-op for this work; nothing about the route config or hooks changed.

The only non-obvious concern is ensuring `/game` (exact, lobby) and `/game/:sessionId` (dynamic) resolve correctly. In RR7 `<Routes>`, all paths are exact by default and the router picks the best-specificity match — `"/game"` and `"/game/:sessionId"` coexist without conflict as sibling `<Route>` elements.

**Primary recommendation:** Sibling flat routes, no nesting needed. Extract ArchivedSessions JSX into its own component (or inline as a tab slot) sharing the existing `useQuery`. Update three `navigate("/")` calls in GameSession to `navigate("/game")`.

---

## Routing Analysis

### React Router v7 in This Codebase

The app uses:
- `BrowserRouter` wrapper in `main.tsx`
- `<Routes>` + `<Route>` declarative config in `App.tsx`
- No `createBrowserRouter`, no `RouterProvider`, no data-layer features

This is the "framework-agnostic" / legacy mode. RR7 did not change the `<Routes>` matching algorithm or any hook signatures for this mode. All RR6 knowledge applies directly.

### `/game` Exact vs `/game/:sessionId` — No Conflict

In `<Routes>`, the router scores each candidate route against the current URL and picks the highest-specificity match. A static segment scores higher than a dynamic segment. Given these two sibling routes:

```tsx
<Route path="/game" element={<GameLobby />} />
<Route path="/game/:sessionId" element={<GameSession />} />
```

- `/game` → matches first route only (no dynamic segment present)
- `/game/42` → matches second route only (`42` fills `:sessionId`)
- `/game/` (trailing slash) → RR7 strips trailing slashes; matches first route

**No ambiguity, no nesting required.** Flat siblings is the correct approach.

### The `*` Catch-All

The current catch-all is:
```tsx
<Route path="*" element={<Navigate to="/" replace />} />
```

Since `/` is being removed as a route, this must change to `<Navigate to="/game" replace />`. Otherwise bare navigation to a non-existent path would redirect to a 404 loop — `/` would match `*`, redirect to `/`, which matches `*`, and so on.

Also: the onboarding guard in App.tsx checks `location.pathname !== "/settings"`. This remains correct as-is; no change needed there.

### Complete Route Change Set in App.tsx

| Before | After |
|--------|-------|
| `<Route path="/" element={<GameLobby />} />` | `<Route path="/game" element={<GameLobby />} />` |
| `<Route path="/game/:sessionId" element={<GameSession />} />` | unchanged |
| `<Route path="/archived" element={<ArchivedSessions />} />` | removed |
| (none) | `<Route path="/search" element={<SearchPlaceholder />} />` |
| `<Route path="*" element={<Navigate to="/" replace />} />` | `<Route path="*" element={<Navigate to="/game" replace />} />` |

`ArchivedSessions` import stays in App.tsx only if GameLobby imports and uses it directly; alternatively the import moves to GameLobby.tsx. The standalone `ArchivedSessions` page import can be removed from App.tsx once it's no longer a route.

---

## Navigate("/") Calls — Must Update

Two places in `GameSession.tsx` navigate to `"/"` after archive/delete. Both must change to `"/game"`:

| File | Line | Context |
|------|------|---------|
| `src/pages/GameSession.tsx` | 363 | `archiveMutation` `onSuccess` callback |
| `src/pages/GameSession.tsx` | 714 | Inline `.then(() => navigate("/"))` on End Session button |

These are the only `navigate("/")` calls in the codebase. Missing them means users land on a blank page (no route matches `/` after the change).

---

## ArchivedSessions Tab Embed Strategy

### Current Structure

`ArchivedSessions` is a standalone page component with:
- Its own `useQuery(["archivedSessions"], api.listArchivedSessions)` — `staleTime: 30000`
- Its own `useState` for the delete dialog (`deleteSessionId`)
- A `useNavigate` for `navigate(`/game/${session.id}`)` — this still works after the route change
- A delete mutation with `queryClient.invalidateQueries(["archivedSessions"])`
- A `Dialog` for delete confirmation

### Recommended Embed Approach: Extract Inner Content

GameLobby already imports `Tabs` / `TabsList` / `TabsTrigger` / `TabsContent` from shadcn. The cleanest approach is:

1. Extract the content body of `ArchivedSessions` (everything inside the outer `<div>`) into a new colocated component — call it `ArchivedSessionsTab` — in the same file or a sibling file.
2. `ArchivedSessionsTab` owns its own `useQuery` and `useState` internally. No prop drilling, no lifting state.
3. `GameLobby` wraps its existing grid view in `<TabsContent value="active">` and adds `<TabsContent value="archived"><ArchivedSessionsTab /></TabsContent>`.

The outer wrapper divs from `ArchivedSessions` (the `min-h-screen` centering layout, the page-level `<h1>`) are discarded — the tab context replaces them.

### Why Not Just Import ArchivedSessions Directly?

The existing `ArchivedSessions` component has a full-page layout (`min-h-screen flex flex-col items-center ... p-6 gap-8`). Rendering it inside a tab would create a double-padded nested full-page layout. The outer wrapper must be stripped — hence extracting the inner content into a tab-specific component is cleaner than fighting the existing layout.

### shadcn Tabs Usage Pattern in GameLobby

GameLobby already uses `Tabs` for the session-creation form (Search Title / Import Chain). The outer lobby tab set will be a new `Tabs` wrapping the session grid / archived content. The existing inner `Tabs` for the creation form remains nested — shadcn Tabs supports nesting with distinct `value` namespaces.

```tsx
// Outer tabs (lobby-level) — new
<Tabs defaultValue="active">
  <TabsList>
    <TabsTrigger value="active">Active</TabsTrigger>
    <TabsTrigger value="archived">Archived</TabsTrigger>
  </TabsList>
  <TabsContent value="active">
    {/* existing session grid + new session form */}
  </TabsContent>
  <TabsContent value="archived">
    <ArchivedSessionsTab />
  </TabsContent>
</Tabs>
```

The inner `Tabs` (for search/CSV in the creation form) sits entirely inside `TabsContent value="active"`, so there is no value collision.

### Query Behavior

`ArchivedSessionsTab`'s `useQuery(["archivedSessions"])` will only execute when the Archived tab is mounted. shadcn `TabsContent` renders its children into the DOM by default (not lazy), but the query is set up with `staleTime: 30000` which is fine — it fetches once and caches. No special enabling logic needed.

If lazy rendering is desired (skip fetch until tab is visited), set `enabled: false` until first visit using a `useState` flag. But given the existing `staleTime: 30000`, this is optional and not required for correctness.

---

## NavBar Active State Logic

### New Logic for Three Items

| Nav Item | Active When | Logic |
|----------|-------------|-------|
| Game Mode | at `/game` or inside any game session | `pathname === "/game" \|\| pathname.startsWith("/game/")` |
| Search | at `/search` | `pathname === "/search"` |
| Settings | at `/settings` | implied by existing pattern — icon-only, no active highlight currently applied |

**Game Mode active-state note:** The current `isSessionsActive` already uses `pathname === "/" || pathname.startsWith("/game/")`. Change the `=== "/"` arm to `=== "/game"`. That's the only change needed.

**Settings active state:** Looking at the existing NavBar, Settings has no active-state class applied — it's always rendered with `text-muted-foreground hover:text-foreground`. This is the existing pattern and should be preserved (icon-only buttons conventionally don't show a persistent active bg).

### Revised NavBar Active Checks

```tsx
const isGameModeActive = pathname === "/game" || pathname.startsWith("/game/")
const isSearchActive = pathname === "/search"
// Settings: no active class (existing pattern)
```

### Logo Link

The logo currently links to `"/"`. It should link to `"/game"` after the route change — otherwise clicking the logo goes to a 404 (caught by `*` redirect, but momentarily visible). This is a one-line change in NavBar.

---

## Search Placeholder Component

A new component is needed. Minimal — no logic, no queries:

```tsx
// src/pages/SearchPlaceholder.tsx
export default function SearchPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-start p-6 mt-16">
      <div className="w-full max-w-2xl">
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <h1 className="text-2xl font-bold tracking-tight">Search</h1>
          <p className="text-muted-foreground mt-2">Coming soon.</p>
        </div>
      </div>
    </div>
  )
}
```

No back button. No other affordances. Uses the app's card aesthetic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Active route highlighting | Manual pathname comparisons beyond what's needed | `useLocation().pathname` — already imported and used. No additional library needed. |
| Tabs | Custom toggle UI | `Tabs/TabsList/TabsTrigger/TabsContent` from `@/components/ui/tabs` — already imported in GameLobby |

---

## Common Pitfalls

### Pitfall 1: Forgetting navigate("/") in GameSession
**What goes wrong:** After archiving a session, the user is redirected to a blank page because `/` has no route.
**Why it happens:** Two `navigate("/")` calls in GameSession.tsx exist — one in `archiveMutation.onSuccess` (line 363) and one in the inline End Session button handler (line 714). Both must change to `"/game"`.
**Warning signs:** Archive a session → blank page / immediate redirect to `/game` via catch-all (looks like a flash).

### Pitfall 2: Outer layout from ArchivedSessions bleeds into tab
**What goes wrong:** Rendering `<ArchivedSessions />` directly inside a TabsContent gives a double-padded full-page layout (`min-h-screen p-6`) inside an already-padded page.
**How to avoid:** Extract only the inner content (the session list + delete dialog) into `ArchivedSessionsTab`. Drop the outer centering wrapper and `<h1>` heading — the tab label provides sufficient context.

### Pitfall 3: Inner Tabs value collision
**What goes wrong:** The new lobby-level `<Tabs defaultValue="active">` and the existing inner `<Tabs key={defaultTab} defaultValue={defaultTab}>` share the same `Tabs` context tree if nested improperly.
**Why it happens:** shadcn Tabs uses React context. Two `<Tabs>` components each create independent contexts — as long as `ArchivedSessionsTab`'s inner Tabs (if any) are children of their own `<Tabs>` root, there is no collision. The inner creation form Tabs live inside `TabsContent value="active"`, which is fine.
**How to avoid:** Ensure each `<Tabs>` component is a distinct root. Do not share `TabsList` between two `<Tabs>` roots.

### Pitfall 4: Trailing slash on /game
**What goes wrong:** Browser navigates to `/game/` (trailing slash), which in some environments doesn't match `path="/game"`.
**Why it happens:** React Router v7 in `BrowserRouter` mode normalizes trailing slashes — `/game/` is treated as `/game`. This is a non-issue in RR7 but worth knowing if the server is also doing URL normalization.
**How to avoid:** No action required; RR7 handles it.

### Pitfall 5: catch-all still points to "/"
**What goes wrong:** `<Route path="*" element={<Navigate to="/" replace />} />` causes an infinite redirect once `/` has no route — any unknown URL → `/` → `*` → `/` loop.
**How to avoid:** Change the catch-all to `<Navigate to="/game" replace />` in the same App.tsx edit.

---

## Complete Change Map

| File | Changes |
|------|---------|
| `src/App.tsx` | Change `path="/"` → `path="/game"`; remove `path="/archived"` route; add `path="/search"` route; update `*` catch-all to `/game`; remove ArchivedSessions import if no longer used as a route (import moves to GameLobby or ArchivedSessionsTab file) |
| `src/components/NavBar.tsx` | Replace Sessions/Archived links with Game Mode (`/game`) and Search (`/search`); update active logic; update logo `to` from `"/"` to `"/game"` |
| `src/pages/GameLobby.tsx` | Wrap session grid in `<Tabs defaultValue="active">`; add Archived tab rendering `<ArchivedSessionsTab />` |
| `src/pages/GameSession.tsx` | Two `navigate("/")` → `navigate("/game")` (lines 363 and 714) |
| `src/pages/ArchivedSessions.tsx` | Extract inner content as `ArchivedSessionsTab` (or create `src/pages/ArchivedSessionsTab.tsx`) — keep the original file for now or delete after extraction |
| `src/pages/SearchPlaceholder.tsx` | New file — placeholder component |

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `frontend/src/App.tsx` — route definitions, onboarding guard
- `frontend/src/components/NavBar.tsx` — active state logic, current nav items
- `frontend/src/pages/GameLobby.tsx` — existing Tabs usage, query keys
- `frontend/src/pages/ArchivedSessions.tsx` — query key, mutations, layout structure
- `frontend/src/pages/GameSession.tsx` — two `navigate("/")` calls at lines 363, 714
- `frontend/package.json` + installed `node_modules` — confirmed react-router-dom@7.13.1, react@18.3.1

### Secondary (HIGH confidence — library behavior)
- React Router v7 docs: `<Routes>` uses best-specificity matching; static segments beat dynamic segments; trailing slashes are normalized. This is unchanged from RR v6 and applies identically in legacy `BrowserRouter` mode.
- shadcn Tabs: each `<Tabs>` is an independent context root; nesting two `<Tabs>` components does not cause value collision.

---

## Metadata

**Confidence breakdown:**
- Route coexistence (`/game` + `/game/:sessionId`): HIGH — verified against RR7 matching rules and existing route patterns
- ArchivedSessions embed: HIGH — direct code inspection of both components; layout pitfall confirmed
- NavBar active logic: HIGH — direct code reading; logic is trivial string comparison
- navigate("/") call sites: HIGH — grepped the full codebase, exactly two instances found

**Research date:** 2026-03-30
**Valid until:** Stable — no external dependencies being introduced; valid as long as codebase structure is unchanged
