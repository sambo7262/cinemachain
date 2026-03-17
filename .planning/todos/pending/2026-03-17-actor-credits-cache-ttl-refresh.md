---
created: 2026-03-17T06:11:20.737Z
title: Actor credits cache TTL refresh
area: api
files:
  - backend/app/routers/game.py
  - backend/app/models/__init__.py
---

## Problem

Actor credits are fetched from TMDB once and cached in Postgres indefinitely. If an actor receives a new credit after their initial cache date, that movie never appears in eligible results — even weeks or months later. Example: actor cached Day 1, new TMDB credit added Day 15, query on Day 20 still returns Day 1 snapshot.

## Solution

Add `last_fetched_at` timestamp column to the Actor (or ActorCredit) table. In `_ensure_actor_credits_in_db`, compare `last_fetched_at` against a TTL (suggested: 30 days). If stale or null, re-fetch credits from TMDB and upsert. This is a background-safe operation — no user-visible latency since it only triggers on actors whose cache has expired, not on every request. A scheduled backend job (e.g. APScheduler or a cron endpoint) could also proactively refresh all cached actors nightly to keep the pool current without any per-request overhead.
