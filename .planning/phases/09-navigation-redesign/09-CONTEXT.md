# Phase 9: Navigation Redesign — Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the top navigation so **Game Mode | Search | Settings** are permanently visible on every page. Lay the routing foundation for Search (Phase 10). Merge Archived Sessions into Game Mode as a tab. No behaviour changes to existing game functionality.

</domain>

<decisions>
## Implementation Decisions

### Nav labels and structure
- Three permanent nav items: **Game Mode**, **Search**, **Settings**
- "Search" is the label (not "Query Mode") — simpler, immediately understood
- Settings remains icon-only (gear icon, existing treatment)
- Active state highlight on the current section, same pattern as today

### Game Mode destination
- Game Mode routes to `/game` (new URL — lobby moves from `/` to `/game`)
- No redirect from `/` to `/game` — just set `/game` as the canonical URL and update routing accordingly
- Lobby page content and appearance unchanged — no new heading needed; context is obvious when playing

### Archived Sessions — merged into Game Mode
- `/archived` route removed entirely (no redirect needed — not a shareable URL)
- Archived sessions surface as a tab within the Game Mode page: **Active | Archived**
- Default tab on landing: **Active**
- Tab state is not persisted — always opens to Active

### Search placeholder (Phase 10 not yet built)
- `/search` route renders a placeholder page
- Styled to match the app's card/panel aesthetic (dark card, centered)
- Copy: "Search" heading + "Coming soon." below — clean and minimal
- No back-button or navigation affordance — top nav is sufficient

</decisions>

<code_context>
## Relevant Existing Code

**NavBar.tsx** (`frontend/src/components/NavBar.tsx`)
- Currently: `Sessions | Archived | ⚙` (icon-only Settings)
- Active state uses `bg-accent text-accent-foreground` on the active link
- isSessionsActive: `pathname === "/" || pathname.startsWith("/game/")`
- isArchivedActive: `pathname === "/archived"`
- Replace with three items: Game Mode (`/game`), Search (`/search`), Settings icon (`/settings`)

**App.tsx** (`frontend/src/App.tsx`)
- Current routes: `/` → GameLobby, `/game/:sessionId` → GameSession, `/archived` → ArchivedSessions, `/settings` → Settings
- Changes needed:
  - `/` → redirect to `/game` OR just set `/game` as the GameLobby route
  - `/game/:sessionId` stays unchanged (individual session route)
  - `/archived` route removed
  - `/search` route added → Search placeholder component
- ArchivedSessions import stays — it will render as a tab inside GameLobby, not a standalone route

**GameLobby.tsx** (`frontend/src/pages/GameLobby.tsx`)
- Currently renders active sessions and new game controls
- Add `Active | Archived` tabs; Archived tab renders the ArchivedSessions content inline
- Default tab: Active

</code_context>
