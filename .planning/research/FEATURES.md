# Feature Research

**Domain:** Home media companion app (Plex/arr-stack integration)
**Researched:** 2026-03-14
**Confidence:** HIGH for table stakes / MEDIUM for differentiators / LOW where marked

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Plex watch history read | Every companion app reads this; it's the base data layer | LOW | Via Plex API `/status/sessions/history/all` or Tautulli |
| TMDB metadata lookup | Standard for all arr-stack tools; posters, ratings, cast | LOW | Free API, 3B+ req/day; returns cast, crew, genres, ratings, posters |
| Radarr integration for movie requests | Users expect 1-click requesting; Overseerr/Ombi both do this | MEDIUM | POST to Radarr API with TMDB ID + rootFolder + quality profile |
| Responsive / mobile-friendly UI | All modern tools (Overseerr, Petio) require this | LOW | CinemaChain is single-user on NAS; at minimum desktop-first is fine |
| Show movie poster + rating + year | Pure table stakes for any media browser; IMDb, Letterboxd, Plex all do this | LOW | Pulled from TMDB |
| Mark watched / unwatched toggle | Long-requested in r/PleX; Plex community specifically asked for this | LOW | Can write back via Plex API or just track locally |
| Filter by genre | Universal expectation in any media app; IMDb, Letterboxd, Plex all support | LOW | TMDB genre field on every movie |
| Sort by rating | Expected in any movie browser; IMDb/Letterboxd default sort option | LOW | TMDB vote_average field |
| Search by movie title or actor name | Both app modes require it; baseline in Overseerr, Ombi, Petio | LOW | TMDB `/search/movie` and `/search/person` endpoints |
| Avoid duplicate requests | Overseerr checks Plex library before showing request button; users expect this | MEDIUM | Check Plex library scan + Radarr queue before showing "Request" |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Actor-chain game mechanic | No existing tool has this; solves decision fatigue by giving structured discovery path | HIGH | Core to CinemaChain identity; "Six Degrees"-inspired but constrained to your own library |
| Session memory (no-repeat actors) | Prevents loop exploitation; makes the chain feel intentional | MEDIUM | Track used actor IDs per session in memory/localStorage |
| "Eligible actors" panel filtered to unwatched filmography | None of Overseerr/Ombi/Petio surface "actors with unwatched movies" — this is novel | HIGH | Requires cross-referencing TMDB filmography with Plex watch state |
| Side-by-side actor + movie panels | UX pattern not seen in existing tools; reduces click depth significantly | MEDIUM | All existing tools are single-panel browse flows |
| Webhook-triggered completion event | Plex webhooks fire on `media.scrobble`; auto-advancing game state is novel | MEDIUM | Plex Pass required for webhooks; fallback is manual "I just watched this" |
| Filter unwatched only (in filmography context) | Overseerr shows everything; users with large libraries want to see what they haven't seen | LOW | Cross-reference TMDB filmography against Plex `/library/all?type=1` |
| Request directly from discovery flow | Overseerr separates discover from request; CinemaChain collapses them into one action | LOW | Single "Request" button in movie panel sends to Radarr inline |
| Radarr + Sonarr both supported in Query Mode | Overseerr supports both; single-user tool should too for TV show requests | MEDIUM | Separate API targets; Sonarr uses series ID not TMDB movie ID |
| Sort filmography by "most connectable" (degree to last actor) | Gamification layer: surfaces actors who appear in most of your unwatched movies | HIGH | Requires graph computation across TMDB credits; fun but complex |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Multi-user request management | Overseerr's whole model; users ask for "family sharing" | For a single-user personal app on Synology NAS, this is scope creep; adds auth complexity, permission layers, approval queues | Stay single-user; use Overseerr if multi-user is needed |
| Push notifications (mobile) | Users want to know when downloads complete | Requires mobile push infrastructure (APNs/FCM), certificates, background services | Discord/webhook notification to existing channel instead |
| Recommendation algorithm ("what should I watch?") | Netflix/Plex both try this; users expect it | ML recommendations require training data and are wrong often enough to erode trust | The actor-chain game IS the recommendation engine — it's deterministic and user-controlled |
| Full Plex player embed | Some tools try to play media in-app | Licensing, codec complexity, DRM; Plex already does this well | Link out to Plex directly; deep-link to specific movie |
| Social features (reviews, follows, public profiles) | Letterboxd model; users love this | For a personal single-user app this is wasted complexity; Letterboxd already exists | Export watch log to Letterboxd if desired |
| Offline / cached library | Users want it to work without internet | TMDB requires internet; Plex API requires local network; caching staleness is a constant bug source | Cache only session-critical data (current session actors); re-fetch on session start |
| Torrent/indexer management | Users conflate arr-stack tooling | Legal gray area; Radarr handles this; not a companion app concern | Surface Radarr's existing queue status only |

---

## Feature Dependencies

```
Plex API (watch history, library)
├── Movie Game Mode
│   ├── Read last-watched movie → requires Plex history endpoint
│   ├── Fetch cast → requires TMDB /movie/{id}/credits
│   ├── Eligible actors panel → requires TMDB filmography + Plex watch state cross-ref
│   ├── Eligible movies panel → requires TMDB /person/{id}/movie_credits + Plex unwatched filter
│   ├── Session actor tracking → requires in-session state store
│   └── Request movie → requires Radarr POST /movie API
│
└── Query Mode
    ├── Search actor → requires TMDB /search/person
    ├── Search movie → requires TMDB /search/movie
    ├── Browse filmography → requires TMDB /person/{id}/movie_credits
    ├── Request movie → requires Radarr POST /movie
    └── Request TV show → requires Sonarr POST /series (with TVDB ID lookup)

Plex Webhooks (optional, Plex Pass)
└── Auto-advance game on watch completion → requires webhook receiver endpoint
    └── Without webhooks: manual "I just finished watching" button triggers same flow

TMDB API
├── Movie metadata (poster, rating, year, genres, runtime)
├── Person metadata (photo, biography, known_for)
├── Movie credits (cast list per film)
└── Person credits (filmography per actor)
```

---

## MVP Definition

### Launch With (v1)

- [x] **Plex watch history read** — the entire game depends on knowing the last-watched movie
- [x] **TMDB cast fetch for a movie** — needed to populate the actor selection panel
- [x] **TMDB filmography fetch for an actor** — needed to populate the movie panel
- [x] **Plex library cross-reference (watched/unwatched)** — core filtering; without it, every movie shows regardless of watch state
- [x] **Session actor tracking (no repeat picks)** — prevents trivial loops; must be in v1 for the game to have meaning
- [x] **Radarr request submission** — the payoff action; without it, the app is read-only and incomplete
- [x] **Side-by-side actor + movie panels** — the defining UX; if this is a list it's just Overseerr
- [x] **Filter: unwatched only toggle** — CinemaChain's primary value; show only what you haven't seen
- [x] **Sort by genre / rating** — basic browsability; users can't navigate 50 movies without this
- [x] **"Already in library" indicator** — avoid requesting duplicates; check Plex library before showing request button

### Add After Validation (v1.x)

- [ ] **Query Mode (actor/movie/genre search)** — second stated mode; add after game mode is stable; trigger: first user wants to browse without a game session
- [ ] **Sonarr integration for TV shows** — widens scope of requests; trigger: user requests a show and has no mechanism
- [ ] **Plex webhook receiver** — auto-advance game on completion; trigger: user complains about manually starting new chains; requires Plex Pass
- [ ] **Persistent watch history display** — show chain history for current session; trigger: user loses track of their chain after 4+ picks
- [ ] **Poster grid view vs list view toggle** — UX quality-of-life; trigger: too many movies in panel, poster grid is faster to scan
- [ ] **"Already in Radarr queue" indicator** — show download progress status; requires Radarr queue poll

### Future Consideration (v2+)

- [ ] **Sort filmography by "most connectable actors"** — gamification depth; requires graph traversal across TMDB credits; defer until core loop is proven fun
- [ ] **Cross-session chain history / saved chains** — lets user replay or continue sessions; defer until they've completed 5+ chains and want to reference them
- [ ] **Letterboxd export** — nice-to-have social layer; build only if user actively uses Letterboxd
- [ ] **Discord notification on download complete** — good for async feedback; build only if webhook approach proves insufficient
- [ ] **Genre-constrained game mode** — "only horror movies" chain; fun variant but adds UI complexity; defer until base game is well-used
- [ ] **Actor popularity / TMDB vote weight in panel** — surfaces bigger names first; TMDB has this field; low priority until panel density is a problem

---

## Competitor Feature Analysis

| Feature | Overseerr / Seerr | Ombi | Petio | CinemaChain Approach |
|---------|-------------------|------|-------|----------------------|
| Movie requests | Yes (full) | Yes (full) | Yes | Yes — inline from discovery panel |
| TV show requests | Yes (seasons/episodes) | Yes (single episodes) | Yes | Query Mode only (Sonarr) |
| Plex auth / user sync | Yes | Yes | Yes | N/A — single user, no auth needed |
| Multi-user permissions | Yes (granular) | Yes | Yes | No — single user by design |
| Media discovery browsing | Trending + recommendations | Basic | Basic + metadata | Actor-chain structured discovery |
| Actor-based film browsing | No | No | No | Yes — core mechanic |
| Watch state filtering | No | No | No | Yes — unwatched filmography filter |
| Session game mechanics | No | No | No | Yes — actor chain, no-repeat rule |
| Radarr integration | Yes | Yes | Yes | Yes |
| Sonarr integration | Yes | Yes | Yes | Query Mode only |
| Notifications | 10+ agents | Email, mobile push, Discord | Basic | Webhook-to-Discord (v1.x) |
| Mobile native app | No (web only) | iOS + Android | Web only | Web only (Synology NAS hosted) |
| Watch history display | No | No | No | Yes — chain history in session |
| Request status tracking | Yes (full queue) | Yes | Yes | Basic (check Radarr queue) |
| TMDB metadata display | Yes | Yes | Yes (detailed) | Yes — poster, rating, genres, cast |
| Decision fatigue solution | No (still a big catalog) | No | No | Yes — game mechanic constrains choice |

---

## Key Insights for CinemaChain

1. **The gap is real.** No existing tool surfaces "actors from your watch history whose unwatched filmography is available to request." Overseerr, Ombi, and Petio are all request-management tools first; discovery is an afterthought.

2. **Decision fatigue is the #1 pain point.** Research shows users spend 16 minutes/day deciding what to watch. The actor-chain mechanic directly solves this by constraining choice to a semantically meaningful path (movies connected by people you already liked watching).

3. **Single-user simplifies everything.** No auth system, no request approval queues, no per-user quotas, no notification routing. Every Overseerr feature related to multi-user management is irrelevant here. This is a significant implementation advantage.

4. **Plex already has actor browsing — but it's limited.** Plex's "Discover Credits" feature lets you tap an actor and see their work, but it only searches within the currently open library, not across all libraries, and has no "unwatched filter" or session memory. CinemaChain extends this pattern with game rules layered on top.

5. **TMDB is the right metadata source.** Radarr, Sonarr, Overseerr all use TMDB IDs internally. Building on TMDB means request IDs will always be compatible with the arr-stack without translation.

6. **Webhooks are a v1.x feature, not v1.** The game works fine with a manual "I just watched this" trigger. Webhooks require Plex Pass and an always-on server endpoint — add them once the core loop is proven.

---

## Sources

- [Overseerr / Seerr GitHub](https://github.com/sct/overseerr) — HIGH confidence
- [Overseerr Guide — RapidSeedBox](https://www.rapidseedbox.com/blog/overseerr-guide) — HIGH confidence
- [Petio.tv](https://petio.tv/) — HIGH confidence
- [Ombi.io](https://ombi.io/) — HIGH confidence
- [Servarr Wiki — Useful Tools](https://wiki.servarr.com/useful-tools) — HIGH confidence
- [Plex Discover Credits Support Article](https://support.plex.tv/articles/discover-credits/) — HIGH confidence
- [Plex Actor Cross-Reference Feature Request Forum Thread](https://forums.plex.tv/t/feature-request-cast-cross-reference-movie-info/44556) — HIGH confidence (first-hand user requests)
- [Tautulli](https://tautulli.com/) — HIGH confidence (watch history API patterns)
- [TMDB API Docs](https://developer.themoviedb.org/reference/intro/getting-started) — HIGH confidence
- [Radarr API Wiki](https://github.com/Radarr/Radarr/wiki/API:Movie) — HIGH confidence
- [Plex API Session History](https://www.plexopedia.com/plex-media-server/api/server/session-history/) — HIGH confidence
- [Letterboxd Features Overview](https://letterboxd.com/) — HIGH confidence
- [UserTesting Streaming Survey — Decision Fatigue](https://www.usertesting.com/resources/reports/stream-fatigue-goes-global) — MEDIUM confidence (general streaming, not Plex-specific)
- [Six Degrees of Kevin Bacon — Wikipedia](https://en.wikipedia.org/wiki/Six_Degrees_of_Kevin_Bacon) — HIGH confidence (game mechanic reference)
- [Plex Future Blog Post 2025](https://www.plex.tv/blog/the-future-of-plex-focused-streamlined-and-ready-for-feedback/) — MEDIUM confidence (strategic direction, not feature details)
- [Petio vs Ombi comparison — CompsMag](https://www.compsmag.com/vs/petio-vs-ombi/) — MEDIUM confidence (third-party comparison)
- [Pulsarr GitHub](https://github.com/jamcalli/Pulsarr) — MEDIUM confidence (shows what the community builds around Plex watchlists)
