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

  getEligibleMovies: (sessionId: number, params?: { actor_id?: number; sort?: string; sort_dir?: string; all_movies?: boolean; search?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params?.actor_id) q.set("actor_id", String(params.actor_id))
    if (params?.sort) q.set("sort", params.sort)
    if (params?.sort_dir) q.set("sort_dir", params.sort_dir)
    if (params?.all_movies) q.set("all_movies", "true")
    if (params?.search) q.set("search", params.search)
    if (params?.page != null) q.set("page", String(params.page))
    if (params?.page_size != null) q.set("page_size", String(params.page_size))
    return apiFetch<PaginatedMoviesDTO>(`/game/sessions/${sessionId}/eligible-movies?${q}`)
  },

  pickActor: (sessionId: number, body: { actor_tmdb_id: number; actor_name: string }) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/pick-actor`, { method: "POST", body: JSON.stringify(body) }),

  requestMovie: (sessionId: number, body: { movie_tmdb_id: number; movie_title: string; skip_actor?: boolean }) =>
    apiFetch<{ status: string; candidates?: Array<{tmdb_id: number; name: string}>; session: GameSessionDTO }>(`/game/sessions/${sessionId}/request-movie`, { method: "POST", body: JSON.stringify(body) }),

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

  searchMovies: (q: string) =>
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
}
