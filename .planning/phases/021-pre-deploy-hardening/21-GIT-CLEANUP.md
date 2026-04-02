# Git Cleanup Checklist — v2.0 Release

**WARNING: These commands are destructive and irreversible on the remote.**
**Run these AFTER all Phase 21 plans are complete and verified.**

---

## Pre-flight

- [ ] All Phase 21 work is committed on `main`
- [ ] `git status` shows a clean working tree
- [ ] `git log --oneline v1.0..HEAD | wc -l` — note the commit count being squashed

## Step 1: Squash all v2 work into one commit

```bash
git reset --soft v1.0
git commit -m "feat: CinemaChain v2.0

Full v2.0 feature set:
- Query Mode: search by movie/actor/genre, Radarr requests
- Session Enhancements: save/shortlist movies within sessions
- Mobile Movie List Redesign: card layout, no horizontal scroll
- MDBList Expansion: IMDB ratings, Metacritic, Letterboxd scores
- TMDB Suggested Movies: recommendations cross-referenced with eligible actors
- Watched History: first-party watch tracking with tile/list views
- Backend Scheduler & IMDB Actor Links hardening
- API Key Security: encryption, masking, log scrubbing
- v2 Bug Fixes & Polish: mobile UI, rating dialog, session tools
- Now Playing: metadata hub with ratings, runtime, MPAA, overview
- Pre-Deploy: API key test buttons, Settings validation"
```

## Step 2: Verify

- [ ] `git log --oneline` shows exactly 2 commits: v1.0 parent + the new v2.0 commit
- [ ] `git diff HEAD~1 --stat` shows the full v2 changeset

## Step 3: Force-push

```bash
git push --force origin main
```

## Step 4: Tag

```bash
git tag v2.0
git tag latest
git push origin v2.0 latest
```

## Step 5: Verify remote

- [ ] GitHub shows 2 commits on main
- [ ] Tags v1.0, v2.0, and latest are visible on GitHub
- [ ] `git log --oneline --all` matches expected state
