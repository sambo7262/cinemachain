---
plan: 11-03
status: complete
---

## Summary
Human verification of Phase 11 Save/Shortlist features — all SESS requirements confirmed.

## Verification Results
- SESS-01: Save star icon on each movie row, fills gold on save, clears on unsave ✓
- SESS-02: Saved movies persist after page refresh (DB-backed) ✓
- SESS-03: Saved filter reduces list to saved movies only; stacks with other filters ✓
- SESS-04: Shortlist icon on each movie row, 6-item cap enforced, shortlist filter works, Clear Shortlist button works, shortlist auto-clears after movie pick ✓

## Post-verification fixes applied
- Cross-page filtering: raised backend page_size cap from 100 → 9999; frontend fetches page_size=9999 when save/shortlist filter active
- Icons moved from poster overlay to dedicated column between poster and title (star top, shortlist below)
- Shortlist filter button updated to use ListCheck icon matching row icon
- Splash dialog save star moved to top-left to avoid conflict with close button
