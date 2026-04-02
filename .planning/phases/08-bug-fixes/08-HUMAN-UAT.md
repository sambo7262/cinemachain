---
status: partial
phase: 08-bug-fixes
source: [08-VERIFICATION.md]
started: 2026-03-31T04:00:00Z
updated: 2026-03-31T04:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Mobile overflow — actor name tab label
expected: At 375px viewport, "via {actor name}" span truncates with ellipsis and does not bleed outside the tab trigger
result: [pending]

### 2. GameLobby tile stat text wrapping
expected: At 375px viewport, session tile stat text wraps to two lines rather than overflowing the tile boundary
result: [pending]

### 3. Movies table sticky columns during scroll
expected: Poster and title columns remain fixed while other columns scroll horizontally; backgrounds prevent content bleed-through
result: [pending]

### 4. BUG-07 Trainspotting session self-heal (NAS)
expected: On the NAS instance, loading the Trainspotting chain session's eligible movies tab now shows results (self-heal re-fetch triggered if credits were missing)
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
