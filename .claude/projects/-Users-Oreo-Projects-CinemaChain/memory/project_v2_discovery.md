---
name: v2 discovery topics
description: Feature ideas and priorities surfaced during v1 close-out for v2 planning
type: project
---

Topics to explore in a v2 discovery session (surfaced 2026-03-22 after v1 archive):

**High priority**
- Query Mode (QUERY-01–07) — search by actor/title/genre, sort, filter, Radarr requests; was v1 scope, never built
- Plex auto-watch sync — re-add as polling-based (not webhook); removes manual Mark as Watched friction
- Stats dashboard — longest chain, most-picked actors, total runtime, favourite genres, chains over time

**Medium priority**
- Alternative chain types — director chains, writer chains, composer chains; TMDB data already available, minimal backend work
- Genre-constrained game mode — lock a session to a genre (e.g., horror-only); extends replay value

**Lower priority / stretch**
- Watchlist — save movies seen during gameplay for later without requesting immediately
- Download complete notification — Discord webhook when Radarr finishes (NOTIF-01 from v1 backlog)
- Dead-end recovery suggestions — instead of "you're stuck," suggest nearby actors to restart the chain
- Mobile/tablet UX pass — narrow-viewport game view for on-the-couch use

**From Phase 13 discuss session (2026-03-31) — deferred to post-v2:**
- MDBList recommendations → Suggested Movies tab (cross-ref MDBList "recommended" with eligible actors in game mode)
- Watched list sync to MDBList — POST all watched movies to a MDBList list for personalized recommendations
- MDBList vs TMDB fallback/redundancy architecture
- IMDB actor links — store `imdb_person_id` from TMDB `/person/{id}/external_ids`, swap ChainHistory actor links
- MDBList tier upgrade evaluation (currently 10k/day paid)

**Why:** Captured at end of v1 close-out conversation + Phase 13 discuss. Surface at v2 close-out / v3 planning.
**How to apply:** Surface these when user starts `/gsd:new-milestone` or asks about v3 planning.
