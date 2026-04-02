const BASE = "/api"

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw Object.assign(new Error(err.detail ?? r.statusText), { status: r.status })
  }
  if (r.status === 204) return undefined as unknown as T
  return r.json()
}

// --- Types ---

export interface CurrentMovieDetail {
  year: number | null
  runtime: number | null
  mpaa_rating: string | null
  overview: string | null
  vote_average: number | null
  imdb_rating: number | null
  rt_score: number | null
  rt_audience_score: number | null
  metacritic_score: number | null
}

export interface GameSessionDTO {
  id: number
  name: string
  status: "active" | "paused" | "awaiting_continue" | "ended" | "archived"
  current_movie_tmdb_id: number
  current_movie_watched: boolean
  steps: GameSessionStepDTO[]
  radarr_status?: string | null
  current_movie_title: string | null    // resolved by backend from Movie table
  watched_count: number
  watched_runtime_minutes: number
  step_count: number           // actor picks made (steps where actor_tmdb_id IS NOT NULL)
  unique_actor_count: number   // distinct actors used
  created_at: string           // ISO 8601 session creation timestamp
  current_movie_detail?: CurrentMovieDetail | null
}

export interface PaginatedMoviesDTO {
  items: EligibleMovieDTO[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface GameSessionStepDTO {
  step_order: number
  movie_tmdb_id: number
  movie_title: string | null
  movie_imdb_id?: string | null
  actor_tmdb_id: number | null
  actor_name: string | null
  watched_at: string | null
  poster_path: string | null
  profile_path: string | null
}

export interface EligibleActorDTO {
  tmdb_id: number
  name: string
  profile_path: string | null
  character: string | null
  is_eligible?: boolean
}

export interface EligibleMovieDTO {
  tmdb_id: number
  title: string
  year: number | null
  poster_path: string | null
  vote_average: number | null
  genres: string | null
  runtime: number | null
  watched: boolean
  selectable: boolean
  via_actor_name: string | null
  vote_count: number | null
  mpaa_rating: string | null
  overview: string | null  // NEW — TMDB plot summary
  rt_score: number | null
  rt_audience_score: number | null
  imdb_id: string | null
  imdb_rating: number | null
  metacritic_score: number | null
  letterboxd_score: number | null
  mdb_avg_score: number | null
  saved: boolean
  shortlisted: boolean
}

export interface MovieSearchResultDTO {
  tmdb_id: number
  title: string
  year: number | null
  poster_path: string | null
}

export interface CsvSuggestion {
  tmdb_id: number
  title: string
  year: number | null
}

export interface CsvUnresolvedRow {
  row: number
  csv_title: string
  suggestions: CsvSuggestion[]
}

export interface CsvActorSuggestion {
  tmdb_id: number
  name: string
}

export interface CsvActorError {
  row: number
  csv_movie_title: string
  csv_actor_name: string
  reason: string
  suggestions: CsvActorSuggestion[]
}

export interface CsvActorOverride {
  row: number
  actor_tmdb_id: number
  actor_name: string
}

export interface CsvValidationResponse {
  status: "validation_required"
  resolved_count: number
  unresolved: CsvUnresolvedRow[]
  actor_errors?: CsvActorError[]
}

export interface CsvOverride {
  row: number
  tmdb_id: number
}

export interface PosterWallItem {
  tmdb_id: number
  poster_path: string
  poster_local_path: string | null
}

export interface SettingsDTO {
  tmdb_api_key: string | null
  radarr_url: string | null
  radarr_api_key: string | null
  radarr_quality_profile: string | null
  tmdb_cache_time: string | null
  tmdb_cache_top_n: string | null
  tmdb_cache_top_actors: string | null
  mdblist_api_key: string | null
  tmdb_suggestions_seed_count: string | null
  mdblist_schedule_time: string | null
  mdblist_refetch_days: string | null
}

export interface SettingsStatusDTO {
  tmdb_configured: boolean
  migrated_from_env: boolean
}

export interface ServiceValidationResult {
  ok: boolean
  error: string | null
  warning: string | null
}

export type ValidateAllResponse = Record<"tmdb" | "radarr" | "mdblist", ServiceValidationResult>

export interface RadarrRequestResult {
  status: "queued" | "already_in_radarr" | "not_found_in_radarr" | "error"
}

export interface WatchedMovieDTO {
  tmdb_id: number
  title: string
  year: number | null
  poster_path: string | null
  vote_average: number | null
  genres: string | null
  runtime: number | null
  mpaa_rating: string | null
  overview: string | null
  rt_score: number | null
  rt_audience_score: number | null
  imdb_id: string | null
  imdb_rating: number | null
  metacritic_score: number | null
  letterboxd_score: number | null
  mdb_avg_score: number | null
  watched_at: string
  personal_rating: number | null
}

export interface WatchedMoviesResponse {
  items: WatchedMovieDTO[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

// --- Game session API ---

export const api = {
  createSession: (body: { start_movie_tmdb_id: number; name: string; start_movie_title?: string }) =>
    apiFetch<GameSessionDTO>("/game/sessions", { method: "POST", body: JSON.stringify(body) }),

  getActiveSession: () =>
    apiFetch<GameSessionDTO | null>("/game/sessions/active"),

  getSession: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}`),

  getEligibleActors: (sessionId: number, include_ineligible?: boolean) => {
    const q = new URLSearchParams()
    if (include_ineligible) q.set("include_ineligible", "true")
    return apiFetch<EligibleActorDTO[]>(`/game/sessions/${sessionId}/eligible-actors?${q}`)
  },

  getEligibleMovies: (sessionId: number, params?: { actor_id?: number; sort?: string; sort_dir?: string; all_movies?: boolean; search?: string; page?: number; page_size?: number; exclude_nr?: boolean }) => {
    const q = new URLSearchParams()
    if (params?.actor_id) q.set("actor_id", String(params.actor_id))
    if (params?.sort) q.set("sort", params.sort)
    if (params?.sort_dir) q.set("sort_dir", params.sort_dir)
    if (params?.all_movies) q.set("all_movies", "true")
    if (params?.search) q.set("search", params.search)
    if (params?.page != null) q.set("page", String(params.page))
    if (params?.page_size != null) q.set("page_size", String(params.page_size))
    if (params?.exclude_nr) q.append("exclude_nr", "true")
    return apiFetch<PaginatedMoviesDTO>(`/game/sessions/${sessionId}/eligible-movies?${q}`)
  },

  pickActor: (sessionId: number, body: { actor_tmdb_id: number; actor_name: string }) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/pick-actor`, { method: "POST", body: JSON.stringify(body) }),

  requestMovie: (sessionId: number, body: { movie_tmdb_id: number; movie_title: string; skip_actor?: boolean; skip_radarr?: boolean }) =>
    apiFetch<{ status: string; candidates?: Array<{tmdb_id: number; name: string}>; session: GameSessionDTO }>(`/game/sessions/${sessionId}/request-movie`, { method: "POST", body: JSON.stringify(body) }),

  renameSession: (sessionId: number, name: string) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/name`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),

  pauseSession: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/pause`, { method: "POST" }),

  resumeSession: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/resume`, { method: "POST" }),

  continueChain: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/continue-chain`, { method: "POST" }),

  endSession: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/end`, { method: "POST" }),

  markCurrentWatched: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/mark-current-watched`, { method: "POST" }),

  getSessionSuggestions: (sessionId: number) =>
    apiFetch<{ suggestion_tmdb_ids: number[] }>(`/game/sessions/${sessionId}/suggestions`),

  importCsv: (
    rows: Array<{ movieName: string; actorName: string; order: number }>,
    name: string,
    overrides?: CsvOverride[],
    actorOverrides?: CsvActorOverride[],
  ) =>
    apiFetch<GameSessionDTO | CsvValidationResponse>("/game/sessions/import-csv", {
      method: "POST",
      body: JSON.stringify({ rows, name, overrides: overrides ?? [], actor_overrides: actorOverrides ?? [] }),
    }),

  searchMoviesLegacy: (q: string) =>
    apiFetch<MovieSearchResultDTO[]>(`/movies/search?q=${encodeURIComponent(q)}`),

  getWatchedMovies: () =>
    apiFetch<MovieSearchResultDTO[]>("/movies/watched"),

  listSessions: () =>
    apiFetch<GameSessionDTO[]>("/game/sessions"),

  listArchivedSessions: () =>
    apiFetch<GameSessionDTO[]>("/game/sessions/archived"),

  archiveSession: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/archive`, { method: "POST" }),

  deleteLastStep: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/steps/last`, { method: "DELETE" }),

  deleteSession: (sessionId: number) =>
    apiFetch<void>(`/game/sessions/${sessionId}`, { method: "DELETE" }),

  getPosterWall: (): Promise<PosterWallItem[]> =>
    apiFetch<PosterWallItem[]>("/movies/poster-wall"),

  getSettings: () => apiFetch<SettingsDTO>("/settings"),

  saveSettings: (settings: Partial<SettingsDTO>) =>
    apiFetch<SettingsDTO>("/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),

  getSettingsStatus: () => apiFetch<SettingsStatusDTO>("/settings/status"),

  validateService: (service: "tmdb" | "radarr" | "mdblist", settings: Partial<SettingsDTO>) =>
    apiFetch<ServiceValidationResult>(`/settings/validate/${service}`, {
      method: "POST",
      body: JSON.stringify(settings),
    }),

  validateAllServices: (settings: Partial<SettingsDTO>) =>
    apiFetch<ValidateAllResponse>("/settings/validate", {
      method: "POST",
      body: JSON.stringify(settings),
    }),

  exportCsv: (sessionId: number, sessionName: string) => {
    fetch(`${BASE}/game/sessions/${sessionId}/export-csv`)
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `chain-${sessionName || sessionId}.csv`
        a.click()
        URL.revokeObjectURL(url)
      })
  },

  // --- Query Mode API (Phase 10) ---

  searchMovies: (q: string) =>
    apiFetch<EligibleMovieDTO[]>(`/search/movies?q=${encodeURIComponent(q)}`),

  searchActors: (q: string) =>
    apiFetch<EligibleMovieDTO[]>(`/search/actors?q=${encodeURIComponent(q)}`),

  getPopularByGenre: (genreId: number) =>
    apiFetch<EligibleMovieDTO[]>(`/movies/popular?genre=${genreId}`),

  requestMovieStandalone: (tmdbId: number) =>
    apiFetch<RadarrRequestResult>(`/movies/${tmdbId}/request`, { method: "POST" }),

  markWatchedOnline: (tmdbId: number) =>
    apiFetch<{ tmdb_id: number; watched: boolean; source: string }>(
      `/movies/${tmdbId}/watched?source=online`, { method: "PATCH" }
    ),

  saveMovie: (sessionId: number, tmdbId: number) =>
    apiFetch<void>(`/game/sessions/${sessionId}/saves/${tmdbId}`, { method: "POST" }),

  unsaveMovie: (sessionId: number, tmdbId: number) =>
    apiFetch<void>(`/game/sessions/${sessionId}/saves/${tmdbId}`, { method: "DELETE" }),

  addToShortlist: (sessionId: number, tmdbId: number) =>
    apiFetch<void>(`/game/sessions/${sessionId}/shortlist/${tmdbId}`, { method: "POST" }),

  removeFromShortlist: (sessionId: number, tmdbId: number) =>
    apiFetch<void>(`/game/sessions/${sessionId}/shortlist/${tmdbId}`, { method: "DELETE" }),

  clearShortlist: (sessionId: number) =>
    apiFetch<void>(`/game/sessions/${sessionId}/shortlist`, { method: "DELETE" }),

  // --- MDBList API (Phase 13) ---

  mdblist: {
    startBackfill: () =>
      apiFetch<{ started: boolean; total: number }>("/mdblist/backfill/start", { method: "POST" }),

    getBackfillStatus: () =>
      apiFetch<{
        running: boolean
        fetched: number
        total: number
        calls_used_today: number
        daily_limit: number
      }>("/mdblist/backfill/status"),

  },

  // --- TMDB Cache API (Phase 17) ---

  cache: {
    runNow: () => apiFetch<{ started?: boolean; running?: boolean }>("/cache/run-now", { method: "POST" }),
    getStatus: () => apiFetch<{ running: boolean; last_run_at: string | null; last_run_duration_s: number | null }>("/cache/status"),
  },

  getDbHealth: () => apiFetch<{
    row_health: {
      total_movies: number
      missing_overview: number
      missing_mpaa: number
      missing_imdb_id: number
      missing_imdb_rating: number
      missing_rt_score: number
      never_mdblist_fetched: number
      total_actors: number
    }
    table_sizes: {
      total_db: string
      movies: string
      credits: string
      actors: string
      watch_events: string
    }
  }>("/settings/db-health"),

  // --- Watch History API (Phase 16) ---

  getWatchedHistory: (params?: {
    sort?: string
    sort_dir?: string
    search?: string
    page?: number
    page_size?: number
  }) => {
    const q = new URLSearchParams()
    if (params?.sort) q.set("sort", params.sort)
    if (params?.sort_dir) q.set("sort_dir", params.sort_dir)
    if (params?.search) q.set("search", params.search)
    if (params?.page != null) q.set("page", String(params.page))
    if (params?.page_size != null) q.set("page_size", String(params.page_size))
    return apiFetch<WatchedMoviesResponse>(`/movies/watched?${q}`)
  },

  setMovieRating: (tmdbId: number, rating: number | null) =>
    apiFetch<{ tmdb_id: number; rating: number | null }>(
      `/movies/${tmdbId}/rating`,
      { method: "PATCH", body: JSON.stringify({ rating }) }
    ),

  saveMovieGlobal: (tmdbId: number) =>
    apiFetch<{ tmdb_id: number; saved: boolean }>(`/movies/${tmdbId}/save`, { method: "POST" }),

  unsaveMovieGlobal: (tmdbId: number) =>
    apiFetch<{ tmdb_id: number; saved: boolean }>(`/movies/${tmdbId}/save`, { method: "DELETE" }),
}
