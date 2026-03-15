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
  return r.json()
}

// --- Types ---

export interface GameSessionDTO {
  id: number
  status: "active" | "paused" | "awaiting_continue" | "ended"
  current_movie_tmdb_id: number
  current_movie_watched: boolean
  steps: GameSessionStepDTO[]
  radarr_status?: string | null
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
}

export interface EligibleActorDTO {
  tmdb_id: number
  name: string
  profile_path: string | null
  character: string | null
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
}

export interface MovieSearchResultDTO {
  tmdb_id: number
  title: string
  year: number | null
  poster_path: string | null
}

// --- Game session API ---

export const api = {
  createSession: (body: { start_movie_tmdb_id: number }) =>
    apiFetch<GameSessionDTO>("/game/sessions", { method: "POST", body: JSON.stringify(body) }),

  getActiveSession: () =>
    apiFetch<GameSessionDTO | null>("/game/sessions/active"),

  getEligibleActors: (sessionId: number) =>
    apiFetch<EligibleActorDTO[]>(`/game/sessions/${sessionId}/eligible-actors`),

  getEligibleMovies: (sessionId: number, params?: { actor_id?: number; sort?: string; all_movies?: boolean; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params?.actor_id) q.set("actor_id", String(params.actor_id))
    if (params?.sort) q.set("sort", params.sort)
    if (params?.all_movies) q.set("all_movies", "true")
    if (params?.page != null) q.set("page", String(params.page))
    if (params?.page_size != null) q.set("page_size", String(params.page_size))
    return apiFetch<PaginatedMoviesDTO>(`/game/sessions/${sessionId}/eligible-movies?${q}`)
  },

  pickActor: (sessionId: number, body: { actor_tmdb_id: number; actor_name: string }) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/pick-actor`, { method: "POST", body: JSON.stringify(body) }),

  requestMovie: (sessionId: number, body: { movie_tmdb_id: number; movie_title: string }) =>
    apiFetch<{ status: string }>(`/game/sessions/${sessionId}/request-movie`, { method: "POST", body: JSON.stringify(body) }),

  pauseSession: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/pause`, { method: "POST" }),

  resumeSession: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/resume`, { method: "POST" }),

  endSession: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/end`, { method: "POST" }),

  markCurrentWatched: (sessionId: number) =>
    apiFetch<GameSessionDTO>(`/game/sessions/${sessionId}/mark-current-watched`, { method: "POST" }),

  importCsv: (rows: Array<{ movieName: string; actorName: string; order: number }>) =>
    apiFetch<GameSessionDTO>("/game/sessions/import-csv", { method: "POST", body: JSON.stringify({ rows }) }),

  searchMovies: (q: string) =>
    apiFetch<MovieSearchResultDTO[]>(`/movies/search?q=${encodeURIComponent(q)}`),

  getWatchedMovies: () =>
    apiFetch<MovieSearchResultDTO[]>("/movies/watched"),
}
